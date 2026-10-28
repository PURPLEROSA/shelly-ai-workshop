# Daily 9:00 check — REEL→PURCHASE

Purpose: the data pull, funnel math, and the scheduled-task setup for Mode 3.

## Insights call

```bash
G=https://graph.facebook.com/v25.0; T="access_token=$META_ACCESS_TOKEN"
F='ad_name,ad_id,spend,impressions,reach,frequency,inline_link_clicks,inline_link_click_ctr,cpm,actions,action_values,cost_per_action_type'
for P in yesterday last_3d maximum; do
  curl -s "$G/$META_AD_ACCOUNT_ID/insights?level=ad&date_preset=$P&fields=$F&action_attribution_windows=[\"7d_click\",\"1d_view\"]&$T" > /tmp/ins_$P.json
done
curl -s "$G/$ADSET_ID?fields=effective_status,learning_stage_info,end_time&$T"
```

## Action types to read from `actions` / `action_values`

| Funnel step | action_type |
|------------|-------------|
| Link clicks | `inline_link_clicks` field |
| Landing page views | `landing_page_view` |
| ViewContent | `offsite_conversion.fb_pixel_view_content` |
| InitiateCheckout | `offsite_conversion.fb_pixel_initiate_checkout` |
| Purchase | `offsite_conversion.fb_pixel_purchase` (value in `action_values`) |

## Math

```
lpv_rate   = landing_page_view / inline_link_clicks
ic_rate    = initiate_checkout / landing_page_view
p_rate     = purchase / initiate_checkout
cpa        = spend / purchase            (— if 0)
roas       = purchase_value / spend
days_left  = sale close − today
```

Cross-check once a day: Purchases in Meta vs. paid documents in Morning. A gap > 20% → flag tracking (Mode 5, last row) before judging any ad.

## Rules for the report

- Learning phase (< 72h since launch / last significant edit): report numbers, recommend nothing except fixes for broken things.
- Never more than 3 recommendations. Each = metric + threshold + money + rollback.
- Ad review rejected / account restricted / pixel `last_fired_time` > 24h → top of report as 🚨, before the numbers.

## Scheduled task (set up once, after launch)

Create a recurring scheduled task in this environment, new session per fire, push notification on:

- Schedule: `CRON_TZ=Asia/Jerusalem 0 9 * * *` (or a few minutes before 9 to avoid the top-of-hour queue)
- Stop it the day after the sale closes.
- Requires in the environment: `META_*` secrets, network access to `graph.facebook.com`, the repo with `ads/state.json`.
- Prompt:

```
Run the REEL→PURCHASE skill, Mode 3 (Morning Check), for the active product in
ads/state.json. Read only — do not change anything in Meta. Produce the Hebrew
morning report from the template, with at most 3 numbered recommendations, and
end by asking Shelly which to approve. If the sale close date has passed,
report final results and recommend stopping this scheduled task.
```
