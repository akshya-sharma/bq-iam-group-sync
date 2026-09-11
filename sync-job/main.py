import os
import logging
import google.auth
from googleapiclient.discovery import build
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Environment variables
BQ_TABLE_ID = os.environ.get("BQ_TABLE_ID", "my-project.private_dataset.group_memberships")
TARGET_GROUPS_ENV = os.environ.get("TARGET_GROUPS", "hr-admins@company.com,finance-users@company.com")
TARGET_GROUPS = [g.strip() for g in TARGET_GROUPS_ENV.split(",") if g.strip()]


def get_cloud_identity_service():
    """Authenticates automatically using the attached GCP Service Account (ADC)."""
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-identity.groups.readonly"]
    )
    return build("cloudidentity", "v1", credentials=credentials)


def get_group_resource_name(service, group_email: str) -> str:
    """Resolves a group email address to its Cloud Identity resource name (e.g. 'groups/0123abc')."""
    resp = service.groups().lookup(groupKey_id=group_email).execute()
    return resp["name"]


def get_transitive_user_emails(service, group_resource_name: str) -> list[str]:
    """Fetches all direct and nested (transitive) user emails in a group."""
    user_emails = []
    page_token = None

    while True:
        resp = (
            service.groups()
            .memberships()
            .searchTransitiveMemberships(
                parent=group_resource_name,
                pageSize=500,
                pageToken=page_token,
            )
            .execute()
        )

        for membership in resp.get("memberships", []):
            keys = membership.get("preferredMemberKey", [])
            if keys and "id" in keys[0]:
                email = keys[0]["id"].lower()
                user_emails.append(email)

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return user_emails


def sync_to_bigquery():
    logging.info("Starting Cloud Identity group membership sync...")
    service = get_cloud_identity_service()
    rows = []

    for group_email in TARGET_GROUPS:
        logging.info("Fetching transitive members for group: %s", group_email)
        group_name = get_group_resource_name(service, group_email)
        member_emails = get_transitive_user_emails(service, group_name)
        for user_email in member_emails:
            rows.append({
                "user_email": user_email,
                "group_email": group_email.lower(),
            })

    bq_client = bigquery.Client()
    job_config = bigquery.LoadJobConfig(
        schema=[
            bigquery.SchemaField("user_email", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("group_email", "STRING", mode="REQUIRED"),
        ],
        # Atomically replaces the table so queries never see empty data during sync
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    job = bq_client.load_table_from_json(rows, BQ_TABLE_ID, job_config=job_config)
    job.result()
    logging.info("Successfully synced %d group memberships to %s.", len(rows), BQ_TABLE_ID)


if __name__ == "__main__":
    sync_to_bigquery()
