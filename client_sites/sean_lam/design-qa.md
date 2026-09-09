# Sean Lam Landing Page — Round 2 QA

## Outcome

- Result: passed.
- Production: https://sean-lam-protection.vercel.app/
- Deployment: `6NdGZbNfnZUmh8i32xcarPNReAJb`, production alias active.
- Full regression: `.venv\Scripts\python.exe verify_project.py` — 48/48 passed.
- Focused regression: `python test_sean_lam_site.py` — passed.

## Visual evidence

- Approved reference: `C:\Users\melvi\Desktop\WhatsApp Image 2026-09-09 at 9.58.23 PM.jpeg`.
- Real supplied portrait: `assets/sean-lam.jpeg`. The AI-generated hero asset is not used.
- Desktop 1280 × 800: rendered height 3612 px versus the previous 4535 px, a 20.4% reduction; hero CTA and portrait focal point fit above the fold.
- Responsive checks: 320, 375, 414 and 768 px; no horizontal overflow and no wrapped clickable label. Mobile sticky WhatsApp CTA appears below 768 px and is hidden at 768 px and above.
- Structure: Hero → problem → calculator → coverage comparison → existing-policy check → Sean / approach → process → audience → question selector → FAQ → final CTA → footer.
- Slop audit: passed all applicable Hallmark gates; no gradients, fake chrome, placeholder testimonial, decorative emoji, fabricated metric or generic card grid.

## Interaction evidence

- Calculator input RM3,000 + RM1,000 × 6 months, RM5,000 savings and RM3,000 benefits returned RM24,000 required and RM16,000 gap.
- Calculator WhatsApp CTA included the months, required amount and estimated gap.
- Existing-policy selection updated the pressed state, CTA label and prefilled WhatsApp message.
- FAQ expanded accessibly; first six questions are visible and two more reveal on demand.
- `?campaign=cashflow` changes the hero to the calculator route; `?campaign=medical-card` changes it to the comparison route.
- Browser console errors: none.

## Tracking and compliance

- Implemented `whatsapp_click`, `calculator_started`, `calculator_completed`, `question_selected`, `faq_opened`, `existing_policy_click`, `final_cta_click` and `scroll_25/50/75/100` with CTA source data.
- Events write to `dataLayer` and call `gtag` / `fbq` when those libraries are configured. No analytics or Pixel ID was invented.
- All WhatsApp links target +60 16-639 6106.
- Insurance copy remains conditional on formal definitions, underwriting and policy terms; no guaranteed claim, price, award, testimonial or Allianz logo is shown.
