local cjson = require("cjson.safe")
local rand = require("resty.openssl.rand")
local cipher_lib = require("resty.openssl.cipher")
local evp = require("resty.evp")

local plugin = {
  PRIORITY = 805,
  VERSION = "0.3.0",
}

local DEFAULT_GATEWAY_PRIVATE_KEY_PATH = "/crypto/gateway_private.pem"
local DEFAULT_CLIENT_PUBLIC_KEY_PATH = "/crypto/client_public.pem"
local DEFAULT_GATEWAY_PRIVATE_KEY_PASSPHRASE_ENV = "CRYPTO_GATEWAY_PRIVATE_KEY_PASSPHRASE"

local key_cache = {
  gateway_decryptors = {},
  client_encryptors = {},
}

local function json_error(status, message)
  return kong.response.exit(status, {
    message = message,
  })
end

local function read_text(path)
  local handle, err = io.open(path, "rb")
  if not handle then
    return nil, err
  end

  local value = handle:read("*a")
  handle:close()
  return value
end

local function decode_envelope(payload)
  local envelope, err = cjson.decode(payload)
  if not envelope then
    return nil, "Encrypted request payload is not valid JSON: " .. (err or "")
  end

  local encrypted_session_key = envelope.encryptedSessionKey and ngx.decode_base64(envelope.encryptedSessionKey)
  local iv = envelope.iv and ngx.decode_base64(envelope.iv)
  local encrypted_payload = envelope.encryptedPayload and ngx.decode_base64(envelope.encryptedPayload)

  if envelope.algorithm ~= "AES/CBC/PKCS5Padding" then
    return nil, "Unsupported algorithm: " .. tostring(envelope.algorithm)
  end
  if not encrypted_session_key then
    return nil, "Missing or invalid encryptedSessionKey"
  end
  if not iv then
    return nil, "Missing or invalid iv"
  end
  if #iv ~= 16 then
    return nil, "Invalid IV length"
  end
  if not encrypted_payload then
    return nil, "Missing or invalid encryptedPayload"
  end

  return {
    encrypted_session_key = encrypted_session_key,
    iv = iv,
    encrypted_payload = encrypted_payload,
  }
end

local function new_aes_cipher()
  local aes_cipher, err = cipher_lib.new("aes-256-cbc")
  if not aes_cipher then
    return nil, "Could not initialize AES cipher: " .. tostring(err)
  end

  return aes_cipher
end

local function decrypt_aes_payload(session_key, iv, encrypted_payload)
  local aes_cipher, err = new_aes_cipher()
  if not aes_cipher then
    return nil, err
  end

  return aes_cipher:decrypt(session_key, iv, encrypted_payload)
end

local function encrypt_aes_payload(session_key, iv, plaintext)
  local aes_cipher, err = new_aes_cipher()
  if not aes_cipher then
    return nil, err
  end

  return aes_cipher:encrypt(session_key, iv, plaintext)
end

local function get_gateway_decryptor(conf)
  local gateway_private_key_path = conf.gateway_private_key_path or DEFAULT_GATEWAY_PRIVATE_KEY_PATH
  local passphrase_env = conf.gateway_private_key_passphrase_env or DEFAULT_GATEWAY_PRIVATE_KEY_PASSPHRASE_ENV
  local passphrase = os.getenv(passphrase_env)
  if not passphrase or passphrase == "" then
    return nil, "Missing gateway private key passphrase environment variable: " .. passphrase_env
  end

  local cache_key = gateway_private_key_path .. "|" .. passphrase
  local cached = key_cache.gateway_decryptors[cache_key]
  if cached then
    return cached
  end

  local pem_private_key, err = read_text(gateway_private_key_path)
  if not pem_private_key then
    return nil, "Could not read gateway private key: " .. tostring(err)
  end

  local decryptor, decrypt_err = evp.RSADecryptor:new(
    pem_private_key,
    passphrase,
    evp.CONST.RSA_PKCS1_PADDING,
    evp.CONST.SHA256_DIGEST
  )
  if not decryptor then
    return nil, "Could not initialize gateway RSA decryptor: " .. tostring(decrypt_err)
  end

  key_cache.gateway_decryptors[cache_key] = decryptor
  return decryptor
end

local function get_client_encryptor(conf)
  local client_public_key_path = conf.client_public_key_path or DEFAULT_CLIENT_PUBLIC_KEY_PATH
  local cached = key_cache.client_encryptors[client_public_key_path]
  if cached then
    return cached
  end

  local pem_public_key, err = read_text(client_public_key_path)
  if not pem_public_key then
    return nil, "Could not read client public key: " .. tostring(err)
  end

  local public_key, public_key_err = evp.PublicKey:new(pem_public_key)
  if not public_key then
    return nil, "Could not initialize client public key: " .. tostring(public_key_err)
  end

  local encryptor, encrypt_err = evp.RSAEncryptor:new(
    public_key,
    evp.CONST.RSA_PKCS1_PADDING,
    evp.CONST.SHA256_DIGEST
  )
  if not encryptor then
    return nil, "Could not initialize client RSA encryptor: " .. tostring(encrypt_err)
  end

  key_cache.client_encryptors[client_public_key_path] = encryptor
  return encryptor
end

local function decrypt_request_payload(conf, envelope)
  local decryptor, err = get_gateway_decryptor(conf)
  if not decryptor then
    return nil, err
  end

  local session_key, decrypt_err = decryptor:decrypt(envelope.encrypted_session_key)
  if not session_key then
    return nil, "Could not decrypt request session key: " .. tostring(decrypt_err)
  end

  local plaintext, plaintext_err = decrypt_aes_payload(session_key, envelope.iv, envelope.encrypted_payload)
  if not plaintext then
    return nil, plaintext_err
  end

  return plaintext
end

local function encrypt_response_payload(conf, plaintext)
  local session_key, rand_err = rand.bytes(32, true)
  if not session_key then
    return nil, rand_err
  end

  local iv, iv_err = rand.bytes(16, true)
  if not iv then
    return nil, iv_err or rand_err
  end

  local encrypted_payload, encrypt_err = encrypt_aes_payload(session_key, iv, plaintext)
  if not encrypted_payload then
    return nil, encrypt_err
  end

  local encryptor, err = get_client_encryptor(conf)
  if not encryptor then
    return nil, err
  end

  local encrypted_session_key, key_err = encryptor:encrypt(session_key)
  if not encrypted_session_key then
    return nil, "Could not encrypt response session key: " .. tostring(key_err)
  end

  return {
    algorithm = conf.algorithm or "AES/CBC/PKCS5Padding",
    encryptedSessionKey = ngx.encode_base64(encrypted_session_key),
    iv = ngx.encode_base64(iv),
    encryptedPayload = ngx.encode_base64(encrypted_payload),
  }
end

function plugin:access(conf)
  kong.service.request.enable_buffering()

  local encrypted_request_payload = kong.request.get_raw_body()
  if not encrypted_request_payload or encrypted_request_payload == "" then
    return json_error(400, "Encrypted request payload is required")
  end

  kong.ctx.shared.crypto_algorithm = conf.algorithm
  kong.ctx.shared.crypto_encrypted_request_payload = encrypted_request_payload

  local envelope, err = decode_envelope(encrypted_request_payload)
  if not envelope then
    return json_error(400, "Gateway could not parse request payload: " .. err)
  end

  local plaintext, err = decrypt_request_payload(conf, envelope)
  if not plaintext then
    return json_error(400, "Gateway could not decrypt request payload: " .. tostring(err))
  end

  kong.ctx.shared.crypto_decrypted_request_payload = plaintext

  kong.service.request.set_header("Content-Type", "application/json")
  kong.service.request.clear_header("Content-Length")
  kong.service.request.set_raw_body(plaintext)
end

function plugin:response(conf)
  local plaintext_response = kong.service.response.get_raw_body()
  if not plaintext_response then
    plaintext_response = kong.response.get_raw_body()
  end
  plaintext_response = plaintext_response or ""

  kong.ctx.shared.crypto_plain_response_payload = plaintext_response

  local encrypted_envelope, err = encrypt_response_payload(conf, plaintext_response)
  if not encrypted_envelope then
    return json_error(500, "Gateway could not encrypt response payload: " .. err)
  end

  local encoded_response = cjson.encode(encrypted_envelope)
  kong.ctx.shared.crypto_encrypted_response_payload = encoded_response

  kong.response.set_header("Content-Type", "application/json")
  kong.response.clear_header("Content-Length")
  kong.response.set_raw_body(encoded_response)
end

return plugin
