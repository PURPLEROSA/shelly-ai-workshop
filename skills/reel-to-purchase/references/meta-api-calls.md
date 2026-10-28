# Meta Marketing API calls — REEL→PURCHASE

Purpose: copy-paste calls for Modes 0, 2, 4. Version `v25.0` (current Feb 2026). On any `(#100)` / unknown-field error: check https://developers.facebook.com/docs/marketing-api/marketing-api-changelog and adjust — don't retry blindly.

```bash
G=https://graph.facebook.com/v25.0
T="access_token=$META_ACCESS_TOKEN"
ACT=$META_AD_ACCOUNT_ID   # "act_123..."
```

Budgets are in the account currency's minor units: ₪120 = `12000`.

## Verify (Mode 0, start of every write session)

```bash
curl -s "$G/me?fields=id,name&$T"
curl -s "$G/$ACT?fields=name,currency,timezone_name,account_status,amount_spent&$T"   # account_status 1 = active
curl -s "$G/$META_PIXEL_ID?fields=name,last_fired_time&$T"
curl -s "$G/$META_IG_USER_ID/media?fields=id,caption,media_type,permalink,timestamp&limit=12&$T"  # pick the 4 reels
```

## 1. Campaign (PAUSED, CBO)

```bash
curl -s -X POST "$G/$ACT/campaigns" -F "$T" \
  -F 'name=Grok Workshop | Sales | 2026-10' \
  -F 'objective=OUTCOME_SALES' \
  -F 'special_ad_categories=[]' \
  -F 'daily_budget=12000' \
  -F 'bid_strategy=LOWEST_COST_WITHOUT_CAP' \
  -F 'status=PAUSED'
```

## 2. Ad set (PAUSED)

```bash
curl -s -X POST "$G/$ACT/adsets" -F "$T" \
  -F 'name=IL 25-60 | Adv+ | IC' \
  -F "campaign_id=$CAMPAIGN_ID" \
  -F 'optimization_goal=OFFSITE_CONVERSIONS' \
  -F 'billing_event=IMPRESSIONS' \
  -F "promoted_object={\"pixel_id\":\"$META_PIXEL_ID\",\"custom_event_type\":\"INITIATED_CHECKOUT\"}" \
  -F 'targeting={"geo_locations":{"countries":["IL"]},"age_min":25,"age_max":60,"targeting_automation":{"advantage_audience":1}}' \
  -F 'end_time=2026-11-02T19:00:00+0200' \
  -F 'status=PAUSED'
```

Switch to Purchase optimization later (≥ 25 purchases / 7d) = new ad set with `custom_event_type=PURCHASE`, not an edit (an edit resets learning anyway).

## 3. Creative from an existing Instagram reel (×4)

```bash
curl -s -X POST "$G/$ACT/adcreatives" -F "$T" \
  -F 'name=Reel 1 creative' \
  -F "object_id=$META_PAGE_ID" \
  -F "instagram_user_id=$META_IG_USER_ID" \
  -F "source_instagram_media_id=$REEL_MEDIA_ID" \
  -F "call_to_action={\"type\":\"LEARN_MORE\",\"value\":{\"link\":\"$LANDING_URL?utm_source=meta&utm_campaign=grok-workshop&utm_content=reel-1\"}}"
```

(`instagram_user_id` replaced the older `instagram_actor_id`. If the API rejects it, check the changelog for the current field.)

## 4. Ad (×4, PAUSED)

```bash
curl -s -X POST "$G/$ACT/ads" -F "$T" \
  -F 'name=Reel 1' -F "adset_id=$ADSET_ID" \
  -F "creative={\"creative_id\":\"$CREATIVE_ID\"}" \
  -F 'status=PAUSED'
```

Save every ID to `ads/state.json`:
```json
{"product":"grok-agents-workshop","campaign_id":"","adset_id":"","ads":{"reel-1":"","reel-2":"","reel-3":"","reel-4":""},"launched_at":null,"last_significant_edit":null}
```

## 5. Launch (only after "מאשרת")

```bash
for ID in $CAMPAIGN_ID $ADSET_ID $AD1 $AD2 $AD3 $AD4; do
  curl -s -X POST "$G/$ID" -F "$T" -F 'status=ACTIVE'; done
curl -s "$G/$AD1?fields=status,effective_status,ad_review_feedback&$T"   # PENDING_REVIEW → ACTIVE
```

## 6. Changes (Mode 4, each after approval)

```bash
curl -s -X POST "$G/$AD_ID" -F "$T" -F 'status=PAUSED'                 # pause one ad
curl -s -X POST "$G/$CAMPAIGN_ID" -F "$T" -F 'daily_budget=14400'       # +20% (₪144)
curl -s -X POST "$G/$ADSET_ID" -F "$T" -F 'end_time=2026-11-09T19:00:00+0200'  # extend sale
curl -s "$G/$ID?fields=status,daily_budget,end_time&$T"                 # read back, always
```
