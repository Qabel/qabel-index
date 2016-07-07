import collections
import os
import io
import math
import struct

from nacl.bindings import crypto_scalarmult_base, crypto_scalarmult

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.hashes import SHA512
from cryptography.hazmat.primitives.hmac import HMAC
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

# NOTE: All assert's here are logical asserts and do NOT depend on input data. I.e. they only explicate the contract.
#       Error handling on the other hand uses NoiseError and other crypto exceptions.

backend = default_backend()


SUITE_NAME = b"Noise255/AES256-GCM\0\0\0\0\0"
H_LEN = 64
CV_LEN_BYTE = 48
SYMM_KEY_LEN_BYTE = 32
NONCE_LEN_BYTE = 12
MAC_BYTES = 16
HEADER_CIPHER_TEXT_LEN_BYTE = 48
PADDING_LEN_BYTES = 4
ASYM_KEY_SIZE_BYTE = 32


DecryptedNoiseBox = collections.namedtuple('DecryptedNoiseBox', 'sender_pubkey contents')


class KeyPair:
    def __init__(self, private_key=None, public_key=None):
        if not private_key:
            private_key = os.urandom(ASYM_KEY_SIZE_BYTE)
        if isinstance(private_key, str):
            private_key = decode_key(private_key)
        assert len(private_key) == ASYM_KEY_SIZE_BYTE
        if not public_key:
            public_key = crypto_scalarmult_base(private_key)
        self.private_key = private_key
        self.public_key = public_key

    def ecdh(self, other_public_key):
        return crypto_scalarmult(self.private_key, other_public_key)


class NoiseError(Exception):
    pass


def our_kdf(secret, extra_secret, info, output_len):
    """
    Noise Key derivation function. Outputs a byte sequence that the caller typically splits into multiple variables
    such as a chain variable and cipher context, or two cipher contexts.

    Args:
        secret:       secret for key derivation
        extra_secret: is used to pass a chaining variable to mix into the KDF.
        info:         ensures that applying the KDF to the same secret values will produce independent output,
                        provided 'info' is different.
        output_len:   length out the output

    Returns:
        derived key of output_len bytes (BytesIO)
    """

    # XXX either I used hkdf below wrong and never managed to use it correctly, or the function we're using ain't
    # XXX the RFC5869 HKDF. Anyway, this is compatible with the Java implementation we have.

    output = io.BytesIO()
    t = bytearray(H_LEN)
    c = 0
    while c <= math.ceil(float(output_len) / H_LEN) - 1:
        bs = b''.join((
            info,
            struct.pack('B', c),
            t[:32],
            extra_secret
        ))

        assert len(bs) == len(info) + 1 + 32 + len(extra_secret)

        hmac = HMAC(key=secret, algorithm=SHA512(), backend=backend)
        hmac.update(bs)
        t = hmac.finalize()
        output.write(t)
        c += 1

    output_val = output.getvalue()[:output_len]
    print(output_val)
    return io.BytesIO(output_val)


def hkdf(secret, extra_secret, info, output_len):
    hkdf = HKDF(algorithm=SHA512(), length=output_len, salt=extra_secret, info=info, backend=backend)
    derived = hkdf.derive(secret)
    print(derived)
    assert len(derived) == output_len
    return io.BytesIO(derived)

_kdf = our_kdf


def _decrypt_aesgcm(key, nonce, ciphertext_tag, associated_data):
    """
    Decrypts a ciphertext with associated data with AES GCM.

    Args:
        key:                encryption key
        nonce:              nonce for encryption
        ciphertext_tag:     ciphertext with appended tag to decrypt
        associated_data:    additional authenticated associated data (the AD in AEAD)

    Returns:
        decrypted plaintext
    """
    if len(ciphertext_tag) < MAC_BYTES:
        raise NoiseError('Truncated ciphertext (length < authentication tag length).')
    algo = algorithms.AES(key)
    assert len(nonce) == 12, 'Expected 96 bit nonce for AES-GCM'
    ciphertext, tag = ciphertext_tag[:-MAC_BYTES], ciphertext_tag[-MAC_BYTES:]
    mode = modes.GCM(nonce, tag)
    decryptor = Cipher(algo, mode, backend).decryptor()
    decryptor.authenticate_additional_data(associated_data)
    try:
        return decryptor.update(ciphertext) + decryptor.finalize()
    except InvalidTag as invalid_tag:
        raise NoiseError('GMAC failure') from invalid_tag


def decrypt_box(receiver_key_pair, noise_box):
    """
    Decrypt a noise box.

    Args:
        receiver_key_pair (KeyPair):    key pair to attempt decryption with
        noise_box:                      bytestream that's supposed to be a noise box

    Returns:
        DecryptedNoiseBox := (sender_pubkey, plaintext_contents)
    """

    def split_key_material(keystream):
        cv, symmetric_key, nonce = keystream.read(CV_LEN_BYTE), keystream.read(SYMM_KEY_LEN_BYTE), keystream.read(NONCE_LEN_BYTE)
        assert len(cv) == CV_LEN_BYTE
        assert len(symmetric_key) == SYMM_KEY_LEN_BYTE
        assert len(nonce) == NONCE_LEN_BYTE
        return cv, symmetric_key, nonce

    cipherstream = io.BytesIO(noise_box)

    # The ephemeral 25519 key is simply prepended to the message
    ephemeral_raw_key = cipherstream.read(ASYM_KEY_SIZE_BYTE)
    if len(ephemeral_raw_key) != ASYM_KEY_SIZE_BYTE:
        raise NoiseError('Could not read ephemeral public key. Not a box or truncated.')

    # Perform first ECDH and HKDF (ECDH of our key and the ephemeral key of the message)
    # This is the part that provides anonymity, since the public key of the sender is only decryptable with our
    # private key.
    info = bytes(SUITE_NAME + b'\0')
    dh1 = receiver_key_pair.ecdh(ephemeral_raw_key)

    key1 = _kdf(dh1, bytes(CV_LEN_BYTE), info, CV_LEN_BYTE + SYMM_KEY_LEN_BYTE + NONCE_LEN_BYTE)
    cv1, symmetric_key1, nonce1 = split_key_material(key1)

    authtext = receiver_key_pair.public_key + ephemeral_raw_key

    header_ciphertext = cipherstream.read(HEADER_CIPHER_TEXT_LEN_BYTE)
    if len(header_ciphertext) != HEADER_CIPHER_TEXT_LEN_BYTE:
        raise NoiseError('Could not read header. Not a box or truncated.')

    sender_raw_key = _decrypt_aesgcm(symmetric_key1, nonce1, header_ciphertext, authtext)

    # Now that we have the authenticated sender public key, we can proceed with the second ECDH-HKDF round
    # (ECDH of our key and the sender's real key). Since the derived key material also depends on the cv1
    # value derived from the random ephemeral key in the first ECDH/HKDF round these keys are of course also per-message
    # random.
    dh2 = receiver_key_pair.ecdh(sender_raw_key)
    info = bytes(SUITE_NAME + b'\1')
    key2 = _kdf(dh2, cv1, info, CV_LEN_BYTE + SYMM_KEY_LEN_BYTE + NONCE_LEN_BYTE)
    _, symmetric_key2, nonce2 = split_key_material(key2)

    # plaintext = noise_body^-1(cc2, body, target_pubkey || header)
    authtext = b''.join((
        receiver_key_pair.public_key,
        ephemeral_raw_key,
        header_ciphertext,
    ))

    body_ciphertext = cipherstream.read()

    padded_plaintext = _decrypt_aesgcm(symmetric_key2, nonce2, body_ciphertext, authtext)

    try:
        encrypted_padding_length, = struct.unpack('>I', padded_plaintext[-PADDING_LEN_BYTES:])
    except ValueError as e:
        raise NoiseError('Invalid padding length.') from e

    total_padding = encrypted_padding_length + PADDING_LEN_BYTES
    plaintext = padded_plaintext[:-total_padding]

    # As per the spec the contents are always UTF-8
    return DecryptedNoiseBox(sender_pubkey=sender_raw_key, contents=plaintext.decode())


def encode_key(key):
    """Return hex-string representation of binary *key*."""
    if len(key) != 32:
        raise ValueError('binary public keys must be 32 bytes')
    return key.hex()


def decode_key(key):
    """Return binary representation of hex-string *key*."""
    if len(key) != 64:
        raise ValueError('hex public keys must be 64 characters long')
    return bytes.fromhex(key)
