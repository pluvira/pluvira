/**
 * Zero-Knowledge E2EE Cloud Backup Architecture Standards.
 * All encryption and decryption operations are delegated to the local backend daemon
 * using PBKDF2 (600,000 iterations) + AES-256-GCM to support all network topologies (HTTP on LAN/IP).
 */

export const PBKDF2_ITERATIONS = 600000;
export const CIPHER_ALGORITHM = 'AES-256-GCM';
const KEY_LENGTH_BITS = 256;
const SALT_BYTE_LENGTH = 16;
const IV_BYTE_LENGTH = 12;

export interface EncryptedPayload {
  encryptedBlob: string;
  sha256Checksum: string;
}

function getSubtleCrypto(): SubtleCrypto {
  if (typeof window === 'undefined' || !window.crypto || !window.crypto.subtle) {
    throw new Error('Web Crypto API (window.crypto.subtle) is not supported in this runtime environment.');
  }
  return window.crypto.subtle;
}

export async function deriveKey(passphrase: string, salt: Uint8Array): Promise<CryptoKey> {
  const subtle = getSubtleCrypto();
  const encoder = new TextEncoder();
  const passphraseKey = await subtle.importKey(
    'raw',
    encoder.encode(passphrase),
    { name: 'PBKDF2' },
    false,
    ['deriveKey']
  );

  return subtle.deriveKey(
    {
      name: 'PBKDF2',
      salt: salt as any,
      iterations: PBKDF2_ITERATIONS,
      hash: 'SHA-256'
    },
    passphraseKey,
    { name: 'AES-GCM', length: KEY_LENGTH_BITS },
    false,
    ['encrypt', 'decrypt']
  );
}

export async function encryptBlob(plaintext: string, passphrase: string): Promise<EncryptedPayload> {
  const subtle = getSubtleCrypto();
  const encoder = new TextEncoder();

  const salt = new Uint8Array(SALT_BYTE_LENGTH);
  window.crypto.getRandomValues(salt);

  const iv = new Uint8Array(IV_BYTE_LENGTH);
  window.crypto.getRandomValues(iv);

  const derivedKey = await deriveKey(passphrase, salt);
  const dataBytes = encoder.encode(plaintext);

  const encryptedBuffer = await subtle.encrypt(
    { name: 'AES-GCM', iv },
    derivedKey,
    dataBytes
  );

  const ciphertext = new Uint8Array(encryptedBuffer);

  const packet = new Uint8Array(salt.length + iv.length + ciphertext.length);
  packet.set(salt, 0);
  packet.set(iv, salt.length);
  packet.set(ciphertext, salt.length + iv.length);

  const hashBuffer = await subtle.digest('SHA-256', packet);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const sha256Checksum = hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');

  let binaryString = '';
  for (let i = 0; i < packet.length; i++) {
    binaryString += String.fromCharCode(packet[i]);
  }
  const encryptedBlob = btoa(binaryString);

  return { encryptedBlob, sha256Checksum };
}

export async function decryptBlob(encryptedBlob: string, passphrase: string): Promise<string> {
  const subtle = getSubtleCrypto();
  const binaryString = atob(encryptedBlob);
  const packet = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    packet[i] = binaryString.charCodeAt(i);
  }

  if (packet.length < SALT_BYTE_LENGTH + IV_BYTE_LENGTH + 16) {
    throw new Error('Corrupted or invalid encrypted backup payload: payload length too short.');
  }

  const salt = packet.slice(0, SALT_BYTE_LENGTH);
  const iv = packet.slice(SALT_BYTE_LENGTH, SALT_BYTE_LENGTH + IV_BYTE_LENGTH);
  const ciphertext = packet.slice(SALT_BYTE_LENGTH + IV_BYTE_LENGTH);

  const derivedKey = await deriveKey(passphrase, salt);

  try {
    const decryptedBuffer = await subtle.decrypt(
      { name: 'AES-GCM', iv },
      derivedKey,
      ciphertext
    );
    const decoder = new TextDecoder();
    return decoder.decode(decryptedBuffer);
  } catch (err: any) {
    throw new Error('Decryption failed: Incorrect passphrase or corrupted backup snapshot.');
  }
}
