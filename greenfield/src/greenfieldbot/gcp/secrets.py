from google.cloud import secretmanager
from greenfieldbot.config import Config
from greenfieldbot.gcp.compute import get_google_credentials


def get_secret_manager_client():
    credentials = get_google_credentials()

    return secretmanager.SecretManagerServiceClient(credentials=credentials)


def get_valheim_password():
    client = get_secret_manager_client()

    secret_name = (
        f"projects/{Config.gcp_project}"
        f"/secrets/{Config.valheim_password_secret}"
        f"/versions/latest"
    )

    response = client.access_secret_version(request={"name": secret_name})

    return response.payload.data.decode("UTF-8")
