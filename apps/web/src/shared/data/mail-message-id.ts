const SAFE_MESSAGE_ID = /^[A-Za-z0-9._~-]+$/;

function base64UrlUtf8(value: string): string {
  const bytes = new TextEncoder().encode(value);
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

export function mailMessagePath(messageId: string): string {
  if (SAFE_MESSAGE_ID.test(messageId)) return encodeURIComponent(messageId);
  return base64UrlUtf8(messageId);
}

export function mailMessageQuery(messageId: string): string {
  return SAFE_MESSAGE_ID.test(messageId) ? "" : "?id_encoding=base64url";
}
