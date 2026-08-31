import unittest


class PublicPolicyTests(unittest.TestCase):
    def test_default_models_are_safe_for_a_clean_install(self):
        from app.public_policy import build_default_model_specs

        without_key = build_default_model_specs(has_boson_key=False)
        enabled_without_key = {
            item["provider_type"] for item in without_key if item["enabled"]
        }
        self.assertEqual(enabled_without_key, {"dummy"})

        with_key = build_default_model_specs(has_boson_key=True)
        enabled_with_key = {
            item["provider_type"] for item in with_key if item["enabled"]
        }
        self.assertEqual(enabled_with_key, {"dummy", "higgs_api"})

    def test_public_health_payload_does_not_expose_local_paths(self):
        from app.public_policy import build_health_payload

        payload = build_health_payload(has_boson_key=False)
        self.assertEqual(
            payload,
            {
                "status": "healthy",
                "version": "0.1.0",
                "boson_api_key_configured": False,
            },
        )
        self.assertNotIn("database_url", payload)

    def test_cors_origins_are_explicit_local_app_origins(self):
        from app.public_policy import PUBLIC_CORS_ORIGINS

        self.assertNotIn("*", PUBLIC_CORS_ORIGINS)
        self.assertIn("http://localhost:5173", PUBLIC_CORS_ORIGINS)
        self.assertIn("http://tauri.localhost", PUBLIC_CORS_ORIGINS)


if __name__ == "__main__":
    unittest.main()
