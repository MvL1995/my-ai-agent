# Sean Lam Site Design QA — Option 3

## Evidence

- Source visual truth: `C:\Users\melvi\Desktop\WhatsApp Image 2026-09-09 at 9.58.23 PM.jpeg`
- Source pixels: 1003 × 1568.
- Browser-rendered implementation: `qa/implementation-option-3-desktop.png`
- Implementation pixels: 1265 × 4535; CSS viewport: 1280 × 720; device scale factor: 1; the 15px width difference is the browser scrollbar.
- Full-view side-by-side: `qa/comparison-option-3-full.png`.
- Focused hero comparison: `qa/comparison-option-3-hero.png` at 2360 × 754.
- Focused about/reasons comparison: `qa/comparison-option-3-about-reasons.png` at 2360 × 717.
- Normalization: source resized from 1003px to the implementation content width of 1180px (1.176×); implementation captured at native 1× density.
- State: desktop default page. Shared target regions compared at the same normalized content width.

## Findings

- No remaining P0, P1, or P2 issue.
- P3: the target uses a WhatsApp brand icon; this dependency-free build keeps a clear text CTA instead of adding an external icon package.
- Accepted difference: the implementation keeps the stronger approved problem/service copy, verified identity table, positive outcome line, calculator, coverage distinction, policy check, consultation flow, intent selector, and eight FAQs. These requested additions make the full page longer than the compact source board.
- Accepted difference: the source's ornamental English keyword block is omitted because the approved content review identified it as unnatural decoration with little information value.

## Required Fidelity Surfaces

- Fonts and typography: the display-serif and supporting sans-serif hierarchy, navy headings, compact uppercase labels, two-line hero headline, thin rules, and editorial number treatment match the selected third direction. The added explanatory copy is smaller than the headline but remains readable.
- Spacing and layout rhythm: the 72px header, 680px integrated hero, immediate about section, three-column reasons, thin dividers, compact FAQ rows, and restrained footer reproduce the target structure. Extra approved modules reuse the same grid and border system instead of introducing cards or a different design language.
- Colors and visual tokens: warm ivory, paper white, deep navy, Allianz-adjacent blue, and pale ice blue map directly to the source. No gradient, glass effect, gold palette, or generic rounded-card grid was added.
- Image quality and asset fidelity: `assets/sean-hero-option-3.png` is a project-local 16:9 identity-preserved hero asset with warm office, right-positioned subject, clean left copy space, and matching plant/background treatment. It contains no text, logo, watermark, CSS drawing, or placeholder.
- Copy and content: hero follows problem → service → action. Insurance wording remains cautious; no guarantee, testimonial, award, premium, payout outcome, or unsupported product claim is present.
- Icons: no fake SVG, emoji, or CSS-drawn WhatsApp icon was introduced; the missing decorative icon is classified P3 because the button label and interaction remain unambiguous.
- Accessibility: semantic landmarks, visible focus styles, form labels, button controls, alt handling, reduced-motion support, and FAQ `aria-expanded` state remain in place.

## Interaction Evidence

- First FAQ changed `aria-expanded` from `false` to `true`, then back to `false`.
- Calculator returned `RM 24,000` for RM 3,000 + RM 1,000 over 6 months.
- WhatsApp CTAs retain the existing prefilled-message URLs and four enquiry intents.
- Browser console errors: none.

## Comparison History

1. Previous implementation `qa/implementation-desktop.png` used a split 730px hero, dark trust bar, oversized section gaps, and placed About after multiple modules. The user correctly rejected it as the wrong option.
2. Reordered the semantic flow to Hero → About → Reasons, removed the dark trust bar, integrated the hero copy and portrait, generated the clean warm-office hero asset, and rebuilt the stylesheet around the selected compact editorial grid.
3. Re-captured the browser output and compared it directly with the supplied third-option screenshot. Hero composition, header, palette, display type, subject position, About treatment, numbered reasons, FAQ treatment, and final CTA now use the selected direction.

## Follow-up Polish

- Add the verified WhatsApp destination number when Sean supplies it; change only the URL base and rerun the focused behavior test.

final result: passed
