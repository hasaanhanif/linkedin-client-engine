"""Read-only connection test and Buffer channel discovery. Never publishes."""
import os
from common import buffer_graphql, generate_with_gemini


def main():
    orgs = buffer_graphql("query { account { organizations { id } } }")
    organizations = (orgs.get("account") or {}).get("organizations") or []
    if not organizations:
        raise RuntimeError("Buffer account has no organizations. Complete Buffer onboarding first.")
    print("Connected Buffer organizations:", len(organizations))
    found = 0
    for org in organizations:
        result = buffer_graphql(
            "query GetChannels($org: OrganizationId!) { channels(input: { organizationId: $org }) { id name service } }",
            {"org": org["id"]},
        )
        for channel in result.get("channels") or []:
            print(f"Channel: {channel['name']} | service: {channel['service']} | id: {channel['id']}")
            if "linkedin" in str(channel.get("service", "")).lower():
                found += 1
    if not found:
        print("WARNING: No LinkedIn channel found. Connect your LinkedIn profile within Buffer.")
    print("Gemini test:", generate_with_gemini('Reply only with this JSON object: {"ok": true}'))
    print("Connections tested. Nothing has been published.")


if __name__ == "__main__":
    main()
