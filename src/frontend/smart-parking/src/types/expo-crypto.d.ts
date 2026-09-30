declare module "expo-crypto" {
  export enum CryptoDigestAlgorithm {
    SHA1 = "SHA-1",
    SHA256 = "SHA-256",
    SHA384 = "SHA-384",
    SHA512 = "SHA-512",
    MD2 = "MD2",
    MD4 = "MD4",
    MD5 = "MD5",
  }

  export enum CryptoEncoding {
    HEX = "hex",
    BASE64 = "base64",
  }

  export function digestStringAsync(
    algorithm: CryptoDigestAlgorithm,
    data: string,
    options?: { encoding: CryptoEncoding },
  ): Promise<string>;

  export function getRandomBytes(length: number): Uint8Array;
  export function getRandomBytesAsync(length: number): Promise<Uint8Array>;
  export function randomUUID(): string;
}
