import os


class Config:
    discord_bot = os.getenv("DISCORD_BOT")

    gcp_project = os.getenv("GCP_PROJECT")
    gcp_zone = os.getenv("GCP_ZONE")
    gcp_instance = os.getenv("GCP_INSTANCE")

    gcp_credentials_file = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS",
        "/var/secrets/google/credentials.json",
    )

    valheim_password_secret = os.getenv(
        "VALHEIM_PASSWORD_SECRET",
        "valheim-server-password",
    )

    @classmethod
    def validate(cls):
        required = {
            "DISCORD_BOT": cls.discord_bot,
            "GCP_PROJECT": cls.gcp_project,
            "GCP_ZONE": cls.gcp_zone,
            "GCP_INSTANCE": cls.gcp_instance,
        }

        missing = [name for name, value in required.items() if not value]

        if missing:
            raise RuntimeError(
                f"Required environment variables are missing: {', '.join(missing)}"
            )
