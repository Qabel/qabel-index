
import pytest

from index_service._crypto import KeyPair, NoiseError, decrypt_box, _decrypt_aesgcm, encode_key, decode_key


def test_random_keypair():
    pair = KeyPair()
    assert len(pair.private_key) == len(pair.public_key) == 32


def test_keypair_from_hex():
    hex = '5AC99F33632E5A768DE7E81BF854C27C46E3FBF2ABBACD29EC4AFF517369C660'
    pair1 = KeyPair(bytes.fromhex(hex))
    pair2 = KeyPair(hex)
    assert len(pair1.private_key) == len(pair1.public_key) == 32
    assert pair1.private_key == pair2.private_key
    assert pair1.public_key == pair2.public_key


def test_keypair_from_hex_short():
    hex = '5AC99F33632E5A768DE7E81BF854C27C46E3FBF2ABBACD29EC4AFF517369C6'
    with pytest.raises(ValueError):
        KeyPair(hex)

def test_keypair_short():
    hex = '5AC99F33632E5A768DE7E81BF854C27C46E3FBF2ABBACD29EC4AFF517369C6'
    with pytest.raises(ValueError):
        KeyPair(bytes.fromhex(hex))


def test_construct_public_key():
    random_pk = bytes.fromhex('77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a')
    expected_pubkey = bytes.fromhex('8520f0098930a754748b7ddcb43ef75a0dbf3a0d26381af4eba4a98eaa9b4e6a')

    assert KeyPair(random_pk).public_key == expected_pubkey


def test_ecdh():
    alice_key = KeyPair('77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a')
    bob_key = KeyPair('5dab087e624a8a4b79e17f8b83800ee66f3bb1292618b6fd1c2f8b27ff88e0eb')
    expected_shared_secret = bytes.fromhex('4a5d9d5ba4ce2de1728e3bf480350f25e07e21c947d19e3376f09b3c1e161742')

    assert alice_key.ecdh(bob_key.public_key) == expected_shared_secret
    assert bob_key.ecdh(alice_key.public_key) == expected_shared_secret


@pytest.mark.parametrize('alice_key,bob_key', [
    (
        KeyPair('5AC99F33632E5A768DE7E81BF854C27C46E3FBF2ABBACD29EC4AFF517369C660'),
        KeyPair('47DC3D214174820E1154B49BC6CDB2ABD45EE95817055D255AA35831B70D3260')
    ),
    (
        KeyPair(),
        KeyPair()
    ),
])
def test_ecdh_agreement(alice_key, bob_key):
    alice_shared_secret = alice_key.ecdh(bob_key.public_key)
    bob_shared_secret = bob_key.ecdh(alice_key.public_key)
    assert alice_shared_secret == bob_shared_secret


def test_decrypt_aesgcm():
    key = bytes.fromhex("120c64583cc9831cedf6b0ffa3cb003c1a3cc057c8f40e3f6fb7f9e376beba43")
    nonce = bytes.fromhex("f5a57de46ff8daee400942c5")
    ciphertext = bytes.fromhex("44178f74e77071918e3f2c3e3d2a256916c33a85f409844bbd1b749719b2f2e71e210f763928d856479e7078cb0413e1")
    aad = bytes.fromhex("1def84acf2c1e5ae04bff2a67b0668bb2c9a285e5c5e033f00c227466c8d022b539edb6df8541fb8e56c97c6a8cd061fe1c6c874a374d8501f8a285ed5ec0922")
    expected_plaintext = bytes.fromhex("1f5349c16e430d7685d56437734d9346c3c842e4a873034d489f480a68e2ed25")

    assert _decrypt_aesgcm(key, nonce, ciphertext, aad) == expected_plaintext


@pytest.mark.parametrize('ciphertext_len', [
    0, 1, 15, 16, 31, 32, 33
])
def test_decrypt_aesgcm_truncated(ciphertext_len):
    # Check that grossly truncated ciphertexts still give the same error, and not something else.
    key = bytes.fromhex("120c64583cc9831cedf6b0ffa3cb003c1a3cc057c8f40e3f6fb7f9e376beba43")
    nonce = bytes.fromhex("f5a57de46ff8daee400942c5")
    with pytest.raises(NoiseError):
        _decrypt_aesgcm(key, nonce, bytes(ciphertext_len), b'')


@pytest.mark.parametrize('plaintext,sender_key,key,box', [
    (
        'yellow submarines',
        '',
        '782e3b1ea317f7f808e1156d1282b4e7d0e60e4b7c0f205a5ce804f0a1a3a155',

        '539edb6df8541fb8e56c97c6a8cd061fe1c6c874a374d8501f8a285ed5ec092244178f74e77071918e3f2c3e3d2'
        'a256916c33a85f409844bbd1b749719b2f2e71e210f763928d856479e7078cb0413e1e25f3e6685caaee9d10b2a'
        '0756d7c1769ccad1ee13bcbaf1186cec727a94b01e2be042da07'
    ),
    (
        'orange submarine',
        '2be41e402667281cfe50699fed0b5d73f753392a6dc277126bd0bfb5217dcf33',
        'a0c2b2bcb68bbe50b01181bfbcbff28ee00f37e44103d3a591dbae6cd5fb9f6a',

        'a63794c4f7033b9c769023f28c12390a7b89296452a4695e35a952625839ae2d9d19715ba2130a6ae49aaf0ea5a'
        'b3eacededbb7676724618abb1fe648328086ed253a75d9672540c319114c4891cc6a1356ae7a8f3c9866c704b14'
        '5efaa0313c9e52f609a4f6c41070ad4741c3ef637e7b7e0a7a7b03a0261607a9'
    )
])
def test_box_from_go_implementation(plaintext, sender_key, key, box):
    sender_key = bytes.fromhex(sender_key)
    key = KeyPair(key)
    box = bytes.fromhex(box)

    sender_pubkey, payload = decrypt_box(key, box)
    assert payload == plaintext
    if sender_key:
        assert sender_pubkey == sender_key


def test_box_corrupted():
    key = KeyPair('a0c2b2bcb68bbe50b01181bfbcbff28ee00f37e44103d3a591dbae6cd5fb9f6a')
    box = bytes.fromhex('a63794c4f7033b9c769023f28c12390a7b89296452a4695e35a952625839ae2d9d19715ba2130a6ae49aaf0ea5a'
                        'b3eacededbb7676724618abb1fe648328086ed253a75d9672540c319114c4891cc6a1356ae7a8f3c9866c704b14'
                        '5efaa0313c9e52f609a4f6c41070ad4741c3ef637e7b7e0a7a7b03a0261607a9')
    for i in range(len(box)):
        box_kaput = bytearray(box)
        box_kaput[i] = 0
        with pytest.raises(NoiseError):
            decrypt_box(key, box_kaput)


def test_box_truncated():
    key = KeyPair('a0c2b2bcb68bbe50b01181bfbcbff28ee00f37e44103d3a591dbae6cd5fb9f6a')
    box = bytes.fromhex('a63794c4f7033b9c769023f28c12390a7b89296452a4695e35a952625839ae2d9d19715ba2130a6ae49aaf0ea5a'
                        'b3eacededbb7676724618abb1fe648328086ed253a75d9672540c319114c4891cc6a1356ae7a8f3c9866c704b14'
                        '5efaa0313c9e52f609a4f6c41070ad4741c3ef637e7b7e0a7a7b03a0261607a9')
    for i in range(len(box)):
        box_kaput = box[:i]
        with pytest.raises(NoiseError):
            decrypt_box(key, box_kaput)


def test_encode_key():
    key = KeyPair()
    result = encode_key(key.public_key)
    assert isinstance(result, str)
    assert len(result) == 64


def test_decode_key():
    key = KeyPair()
    encoded = encode_key(key.public_key)
    decoded = decode_key(encoded)
    assert decoded == key.public_key
