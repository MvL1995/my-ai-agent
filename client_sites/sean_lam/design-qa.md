# Sean Lam Site Design QA

## Evidence

- Source visual truth: `C:\Users\melvi\.codex\generated_images\01a0768a-f926-7471-a20d-87b7af5d8035\exec-6f275ff2-dcc1-4d4f-a271-98ad23e8c29e.png`
- Source pixels: 1003 × 1568.
- Desktop implementation: `qa/implementation-desktop.png`
- Desktop pixels: 1425 × 9182; CSS viewport: 1440 × 1000; device scale factor: 1; the 15px width difference is the browser scrollbar.
- Mobile implementation: `qa/implementation-mobile.png`
- Mobile pixels: 375 × 10863; CSS viewport: 390 × 844; device scale factor: 1; the 15px width difference is the browser scrollbar.
- Mobile first viewport: `qa/implementation-mobile-viewport.png` at 375 × 812.
- Focused side-by-side hero comparison: `qa/comparison-hero.png` at 2880 × 1000.
- State: default page, calculator changed to RM 3,000 + RM 2,000 for 6 months, existing-policy intent selected, first FAQ expanded.

The source is an ideation board rather than a browser-viewport capture. Full-page heights therefore are not treated as pixel-identical targets; the hero comparison normalizes both sides to 1440px width and compares the first 1000px.

## Findings

- No remaining P0, P1, or P2 issue.
- P3: the production WhatsApp number is not in the supplied brief. The prototype uses WhatsApp's generic prefilled-message URL and does not invent a destination number. Add the verified number before public deployment.
- Accepted difference: the ideation image changed the supplied portrait background. The implementation deliberately uses the original client photo without face or identity alteration.
- Accepted difference: the implementation is longer than the ideation board because the selected user feedback explicitly adds a calculator, distinction section, consultation flow, audience fit, policy check, trust proof, and eight FAQs.

## Required Fidelity Surfaces

- Fonts and typography: editorial Song/Noto-serif fallback for display text and system sans-serif for supporting copy preserve the selected premium hierarchy. Desktop hero is two lines after correction; mobile remains readable without horizontal overflow. Small text is at least 0.82rem and is not used for primary explanations.
- Spacing and layout rhythm: asymmetrical hero, thin dividers, wide desktop margins, alternating editorial two-column sections, and generous vertical rhythm match the chosen direction. At 390px, every section collapses to one column and the measured horizontal overflow is 0px.
- Colors and visual tokens: implementation uses `#071A2B`, `#003781`, `#F5F1E8`, `#CFE9F7`, and white only for the main visual system. No gold, gradient, glass effect, or decorative card grid was added.
- Image quality and asset fidelity: the supplied 1125 × 1125 portrait is served directly, remains sharp at desktop and mobile sizes, and uses responsive `object-fit: cover`. No generated replacement, fake logo, SVG drawing, or placeholder is present.
- Copy and content: hero now follows problem → service → action. Medical-card distinction, product limits, calculator caveat, existing-policy objection, human introduction, consultation process, and FAQ answers use conservative wording. No award, testimonial, price, guarantee, payout outcome, or unsupported product claim is present.

## Interaction Evidence

- Navigation anchors resolve to real page sections.
- Existing-policy selection sets the WhatsApp prefill to: `Hi Sean，我已经有保险，想先检查现有保障有没有重复或缺口。`
- Calculator returned `RM 30,000` for RM 3,000 + RM 2,000 over 6 months.
- First FAQ changed `aria-expanded` from `false` to `true` and removed the answer's `hidden` attribute.
- Whole FAQ rows are buttons with visible hover/focus states; the indicator changes from `＋` to `−`.
- Browser console errors: none.

## Comparison History

1. Initial desktop capture found one P2 hero mismatch: the primary headline wrapped to three lines, while the selected visual uses two.
2. Reduced the desktop display size and kept the second phrase together above 760px; mobile is allowed to wrap naturally.
3. Re-captured at 1440 × 1000. The hero headline now measures 161.75px high at 80.87px line height, confirming two lines. The side-by-side comparison shows the selected editorial structure, palette, portrait prominence, and CTA hierarchy are retained.

## Follow-up Polish

- After Sean provides the verified WhatsApp number, replace only the generic `wa.me/?text=` base with the direct number and rerun the focused behavior test.

final result: passed
