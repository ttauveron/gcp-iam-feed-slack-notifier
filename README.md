# IAM / Audit → Slack Notifier (Cloud Function)

This Cloud Function watches Cloud Asset Inventory feeds and GCS IAM audit logs, then posts role-grant notifications into Slack.

---

## Development

### Requirements

Install runtime dependencies only:
```bash
pip install -r requirements.txt
````
Install everything for local development (tests, lint, type-checks):
```
pip install -r requirements-dev.txt
```

#### Test Locally
```
export SLACK_TOKEN=xoxb-xxxxxxr
export SLACK_CHANNEL=#my_channel
python main.py ./tests/fixtures/asset_project.json
```

### Cloud Setup Example

Create a topic named "iam-changes-feed"
```
projects/MY_PROJECT/topics/iam-changes-feed
```

#### Asset Feed
Create the asset feeds at the organization level :
```bash
gcloud asset feeds create iam-policy-feed --organization=ORG_NUM --content-type=iam-policy --asset-types=".*" --pubsub-topic=projects/MY_PROJECT/topics/iam-changes-feed
```
Create service identity for Cloud Assets:
```
gcloud beta services identity create --service=cloudasset.googleapis.com --project=MY_PROJECT
```
That command should return :
```
Service identity created: service-888721688705@gcp-sa-cloudasset.iam.gserviceaccount.com
```
This service account should automatically be granted `roles/cloudasset.serviceAgent` at the project level, which include topic publish permission.

Create a cloud function named "iam-changes-notifier" subscribing to the topic's events. (https://cloud.google.com/run/docs/triggering/pubsub-triggers)
It notably requires to grant invoker permission to the event arc service account on the cloud function.

Grant `roles/browser` to the cloud function's service account at the organization-level in order to resolve project/folder names from their ID.

#### Log Sink
Since Asset feed doesn't have priorAssetState values for the Bucket resource, we'll need to get that information from audit logs in order to compute the permission grants deltas.

Create an organization-level Log Sink only for bucket IAM changes and pointing to the previously created topic :

```
protoPayload.methodName="storage.setIamPermissions"
protoPayload.serviceName="storage.googleapis.com"
resource.type="gcs_bucket"
protoPayload.serviceData.policyDelta.bindingDeltas.action="ADD"
```

Then grant `roles/pubsub.publisher` on the topic to the GCP service account `service-org-MY_ORG_NUMBER@gcp-sa-logging.iam.gserviceaccount.com` so that the Log Sink can forward logs to the topic.

#### Deploy the cloud function

From the root of this repository:
```
gcloud run deploy iam-changes-notifier --region=MY_REGION --source=.
```

## Running Tests
### From the command line

Run all tests:

```bash
pytest
```
