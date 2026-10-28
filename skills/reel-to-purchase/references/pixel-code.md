# Pixel code — REEL→PURCHASE

Purpose: the exact code Mode 1 commits. Replace `{PIXEL_ID}` with `META_PIXEL_ID` (public, safe to commit).

## 1. Base code — `<head>` of every page

```html
<!-- Meta Pixel -->
<script>
!function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;
n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,
document,'script','https://connect.facebook.net/en_US/fbevents.js');
fbq('init','{PIXEL_ID}');
fbq('track','PageView');
</script>
<noscript><img height="1" width="1" style="display:none"
src="https://www.facebook.com/tr?id={PIXEL_ID}&ev=PageView&noscript=1"/></noscript>
```

## 2. Landing page events — before `</body>`

```html
<script>
(function(){
  var PRODUCT = {value:199, currency:'ILS', content_name:'grok-agents-workshop', content_type:'product'};

  // ViewContent: once, when the price/program section is actually seen
  var target = document.querySelector('#signup') || document.querySelector('[data-price]');
  if (target && 'IntersectionObserver' in window) {
    var seen = false;
    new IntersectionObserver(function(entries, obs){
      if (!seen && entries[0].isIntersecting) { seen = true; fbq('track','ViewContent',PRODUCT); obs.disconnect(); }
    }, {threshold:0.4}).observe(target);
  }

  // InitiateCheckout: any link to Morning. Strip fbclid, keep UTMs.
  var utm = new URLSearchParams(location.search);
  document.querySelectorAll('a[href*="mrng.to"],a[href*="greeninvoice"]').forEach(function(a){
    var url = new URL(a.href);
    url.searchParams.delete('fbclid');
    ['utm_source','utm_campaign','utm_content'].forEach(function(k){ if (utm.get(k)) url.searchParams.set(k, utm.get(k)); });
    a.href = url.toString();
    a.addEventListener('click', function(){ fbq('track','InitiateCheckout',PRODUCT); });
  });
})();
</script>
```

If the CTA is built in JS (e.g. `href="${SIGNUP}"` in a template), hook the event where the link is rendered, not with the selector above.

## 3. `thanks.html` — Purchase, exactly once

Set as Morning's success redirect: `https://<site>/thanks.html?paid=1`. If Morning appends its own order/document params, prefer them as the order id.

```html
<script>
(function(){
  var q = new URLSearchParams(location.search);
  if (!q.get('paid') && !q.get('docId') && !q.get('transaction_id')) return; // direct visit → no Purchase
  var orderId = q.get('docId') || q.get('transaction_id') || ('d' + new Date().toISOString().slice(0,10));
  var key = 'fb_purchase_' + orderId;
  try { if (localStorage.getItem(key)) return; localStorage.setItem(key,'1'); } catch(e){}
  fbq('track','Purchase',
      {value:199, currency:'ILS', content_name:'grok-agents-workshop'},
      {eventID: 'purchase_' + orderId});   // same id as any CAPI duplicate → deduplicated
})();
</script>
```

Page content (Hebrew, RTL, on-brand): "נרשמת! 🎉", both dates + 20:00, "קישור הזום יגיע למייל", add-to-calendar links, WhatsApp/contact.

## 4. Route B — Morning can't redirect

Purchase is sent server-side via the Conversions API, from the Morning sales list (export or Morning API), during the 9:00 check — after Shelly approves the list.

```bash
curl -s -X POST "https://graph.facebook.com/v25.0/$META_PIXEL_ID/events" \
  -F "access_token=$META_ACCESS_TOKEN" \
  -F 'data=[{
    "event_name":"Purchase",
    "event_time": EPOCH_SECONDS_OF_PAYMENT,
    "event_id":"purchase_MORNING_DOC_ID",
    "action_source":"website",
    "event_source_url":"https://<site>/",
    "user_data":{"em":["SHA256_LOWERCASE_EMAIL"],"ph":["SHA256_972PHONE_DIGITS_ONLY"]},
    "custom_data":{"value":199,"currency":"ILS"}
  }]'
```

- Hash with SHA-256 after normalizing: email trimmed+lowercase; phone digits only with country code (`9725XXXXXXXX`).
- `event_time` must be within the last 7 days.
- Upgrade path (optional): Morning webhook → Supabase Edge Function → this call, automatic. Verify Morning offers a webhook for paid documents before building.
- Never commit buyer data. Hash in memory, send, discard.
