# Snowflake & CoCo Integration

## Selected Marketplace Dataset
We are integrating Kavach with real-world threat intelligence to provide additional context on indicators of compromise.

- **Name**: Deep and Darkweb Malware Insights - Sample
- **Provider**: Cybersixgill
- **Database/Schema/View**: `DARKFEED.MALWARE_INSIGHTS_VIEW`
- **Description**: This dataset contains Virustotal links that appeared on dark web sites, malware available for download from file-sharing sites, and hashes attributed to malware discovered on the dark and deep web.

### Join Context
In Kavach, when an indicator (like a URL or a crypto address) is extracted from a scanned message, we can query `DARKFEED.MALWARE_INSIGHTS_VIEW` to see if that indicator matches any known threat actor campaigns or has a `sixgill_confidence` score.
The relevant view in our pipeline is `V_CONTEXT_STUB`, which we will replace or extend to `V_CONTEXT_CYBERSIXGILL` to perform `JOIN`s on `external_reference` or `pattern` fields where applicable.

## CoCo (Cortex Copilot) Usage
*Note: Include your screenshots of Cortex Copilot in the `docs/coco/` directory.*

**Prompt Used:**
> "Find hashes that might serve as malwares targeting your organization that are not detectable by VirusTotal"

**CoCo SQL Answer:**
```sql
SELECT * FROM DARKFEED.MALWARE_INSIGHTS_VIEW WHERE(external_reference[0]:positive_rate='low');
```

This interaction demonstrates the use of CoCo to explore the structure and query syntax for the Cybersixgill dataset.
