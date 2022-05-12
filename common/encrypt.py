import os
import hmac
import base64
import hashlib

import OpenSSL
from OpenSSL import crypto
from Cryptodome import Random
from OpenSSL.crypto import FILETYPE_PEM
from Cryptodome.Hash import SHA
from passlib.context import CryptContext
from Cryptodome.Cipher import AES, PKCS1_v1_5
from Cryptodome.PublicKey import RSA
from Cryptodome.Util.Padding import pad, unpad


class AESUtil:
    """
    aes 加密与解密
    """

    def __init__(self, key: str, style="pkcs7", mode=AES.MODE_ECB):
        self.mode = mode
        self.style = style
        self.key = base64.b64decode(key.encode())

    def encrypt_data(self, data: str):
        data = data.encode()
        aes = AES.new(self.key, self.mode)
        pad_data = pad(data, AES.block_size, style=self.style)
        return str(base64.encodebytes(aes.encrypt(pad_data)), encoding="utf8").replace("\n", "")

    def decrypt_data(self, data: str):
        data = data.encode()
        aes = AES.new(self.key, self.mode)
        pad_data = pad(data, AES.block_size, style=self.style)
        return str(unpad(aes.decrypt(base64.decodebytes(pad_data)), block_size=AES.block_size).decode("utf8"))

    @staticmethod
    def generate_key(length=256) -> str:
        random_key = os.urandom(length)
        private_key = hashlib.sha256(random_key).digest()
        return base64.b64encode(private_key).decode()


class RSAUtil:
    """
    RSA 加密 签名
    """

    def __init__(self, pub_key_path: str, private_key_path: str, password: str):
        self.password = password
        with open(private_key_path, "rb") as f:
            self.private_key = f.read()
        with open(pub_key_path, "rb") as f:
            self.pub_key = f.read()

    def encrypt(self, text: str, length=200) -> str:
        """
        rsa 加密
        """
        key = RSA.import_key(self.pub_key)
        cipher = PKCS1_v1_5.new(key)
        res = []
        for i in range(0, len(text), length):
            text_item = text[i : i + length]
            cipher_text = cipher.encrypt(text_item.encode(encoding="utf-8"))
            res.append(cipher_text)
        return base64.b64encode(b"".join(res)).decode()

    def decrypt(self, text: str):
        """
        rsa 解密
        """
        key = RSA.import_key(self._get_private_key())
        cipher = PKCS1_v1_5.new(key)
        return cipher.decrypt(base64.b64decode(text), Random.new().read(15 + SHA.digest_size)).decode()

    def _get_private_key(self,):
        """
        从pfx文件读取私钥
        """
        pfx = crypto.load_pkcs12(self.private_key, self.password.encode())
        res = crypto.dump_privatekey(crypto.FILETYPE_PEM, pfx.get_privatekey())
        return res

    def sign(self, text) -> str:
        """
        rsa 签名
        """
        p12 = OpenSSL.crypto.load_pkcs12(self.private_key, self.password.encode())
        pri_key = p12.get_privatekey()
        return base64.b64encode(OpenSSL.crypto.sign(pri_key, text.encode(), "sha256")).decode()

    def verify(self, sign, data: str):
        """
        验签
        """
        key = OpenSSL.crypto.load_certificate(FILETYPE_PEM, self.pub_key)
        return OpenSSL.crypto.verify(key, base64.b64decode(sign), data.encode(), "sha256")


class HashUtil:
    @staticmethod
    def md5_encode(s: str) -> str:
        """
        md5加密, 16进制
        """
        m = hashlib.md5(s.encode(encoding="utf-8"))
        return m.hexdigest()

    @staticmethod
    def hmac_sha256_encode(k: str, s: str) -> str:
        """
        hmac sha256加密, 16进制
        """
        return hmac.digest(k.encode(), s.encode(), hashlib.sha256().name).hex()

    @staticmethod
    def sha1_encode(s: str) -> str:
        """
        sha1加密, 16进制
        """
        m = hashlib.sha1(s.encode(encoding="utf-8"))
        return m.hexdigest()


class HashUtilB64:
    @staticmethod
    def md5_encode_b64(s: str) -> str:
        """
        md5加密，base64编码
        """
        return base64.b64encode(hashlib.md5(s.encode(encoding="utf-8")).digest()).decode("utf-8")

    @staticmethod
    def hmac_sha256_encode_b64(k: str, s: str) -> str:
        """
        hmacsha256加密，base64编码
        """
        return base64.b64encode(hmac.digest(k.encode("utf-8"), s.encode("utf-8"), hashlib.sha256().name)).decode(
            "utf-8"
        )

    @staticmethod
    def sha1_encode_b64(s: str) -> str:
        """
        sha1加密，base64编码
        """
        return base64.b64encode(hashlib.sha1(s.encode(encoding="utf-8"))).decode("utf-8")


class SignAuth:
    """
    内部签名工具
    """

    def __init__(self, private_key: str):
        self.private_key = private_key

    def verify(
        self, sign: str, data_str: str,
    ):
        """
        校验sign
        """
        sign_tmp = self.generate_sign(data_str)
        return sign == sign_tmp

    def generate_sign(self, data_str: str) -> str:
        """
        生成sign
        """
        return HashUtilB64.hmac_sha256_encode_b64(self.private_key, data_str)


class PasswordUtil:
    """
    密码工具
    """

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    @classmethod
    def verify_password(cls, plain_password, hashed_password):
        return cls.pwd_context.verify(plain_password, hashed_password)

    @classmethod
    def get_password_hash(cls, plain_password):
        return cls.pwd_context.hash(plain_password)
