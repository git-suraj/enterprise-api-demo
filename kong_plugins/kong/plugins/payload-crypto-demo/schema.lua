local schema = {
  name = "payload-crypto-demo",
  fields = {
    {
      config = {
        type = "record",
        fields = {
          {
            algorithm = {
              type = "string",
              required = true,
              default = "AES/CBC/PKCS5Padding",
            },
          },
          {
            gateway_private_key_path = {
              type = "string",
              required = true,
              default = "/crypto/gateway_private.pem",
            },
          },
          {
            client_public_key_path = {
              type = "string",
              required = true,
              default = "/crypto/client_public.pem",
            },
          },
          {
            gateway_private_key_passphrase_env = {
              type = "string",
              required = true,
              default = "CRYPTO_GATEWAY_PRIVATE_KEY_PASSPHRASE",
            },
          },
        },
      },
    },
  },
}

return schema
