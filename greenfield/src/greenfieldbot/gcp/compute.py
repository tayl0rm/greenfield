from google.oauth2 import service_account
from googleapiclient import discovery
from greenfieldbot.config import Config


def get_google_credentials():
    return service_account.Credentials.from_service_account_file(
        Config.gcp_credentials_file
    )


def get_compute_service():
    credentials = get_google_credentials()

    return discovery.build(
        "compute",
        "v1",
        credentials=credentials,
    )


def get_instance(service):
    return (
        service.instances()
        .get(
            project=Config.gcp_project,
            zone=Config.gcp_zone,
            instance=Config.gcp_instance,
        )
        .execute()
    )


def start_instance(service):
    return (
        service.instances()
        .start(
            project=Config.gcp_project,
            zone=Config.gcp_zone,
            instance=Config.gcp_instance,
        )
        .execute()
    )


def stop_instance(service):
    return (
        service.instances()
        .stop(
            project=Config.gcp_project,
            zone=Config.gcp_zone,
            instance=Config.gcp_instance,
        )
        .execute()
    )


def get_external_ip(instance):
    interfaces = instance.get("networkInterfaces", [])

    if not interfaces:
        return None

    access_configs = interfaces[0].get("accessConfigs", [])

    if not access_configs:
        return None

    return access_configs[0].get("natIP")
