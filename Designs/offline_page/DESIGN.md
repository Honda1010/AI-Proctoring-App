# Design System Specification: The Ethereal Authority

## 1. Overview & Creative North Star
**Creative North Star: "The Digital Sanctuary"**

This design system moves away from the aggressive, "big brother" aesthetic typically associated with AI proctoring. Instead, it establishes a high-end, editorial experience that feels like a quiet, prestigious examination hall. We achieve this through **Soft Minimalism**: a philosophy that replaces rigid structural lines with tonal depth, breathing room, and glass-morphism.

The system breaks the "template" look by using intentional asymmetry—pairing large, airy display typography with dense, technical data clusters. We treat the interface as a series of physical layers of frosted glass and fine paper, where importance is defined by "lift" rather than "lines."

---

## 2. Color & Surface Philosophy
The palette is a sophisticated interplay between the professional depth of Dark Navy and the technical clarity of Light Blue.

### The "No-Line" Rule
**Traditional 1px borders are strictly prohibited for sectioning.** Boundaries must be defined solely through background color shifts or tonal transitions.
*   **Context:** To separate a sidebar from a main content area, place a `surface-container-low` (#f3f4f5) sidebar against a `surface` (#f8f9fa) main canvas.
*   **The Ghost Border Fallback:** If a border is required for accessibility (e.g., input fields), use the `outline-variant` token at **20% opacity**. Never use 100% opaque borders.

### Surface Hierarchy & Nesting
Treat the UI as a series of nested tiers to create "natural" depth:
1.  **Canvas (Base):** `surface` (#f8f9fa)
2.  **Sectioning:** `surface-container-low` (#f3f4f5)
3.  **Content Cards:** `surface-container-lowest` (#ffffff)
4.  **Floating Overlays:** `surface-bright` (#f8f9fa) with backdrop-blur.

### The Glass & Gradient Rule
To provide "soul" to the technical AI environment:
*   **Glassmorphism:** For floating modals and proctoring overlays, use `surface-container-lowest` at 70% opacity with a `24px` backdrop-blur.
*   **Signature Gradients:** Use a subtle linear gradient for primary actions and hero states: `primary` (#006687) to `primary-container` (#41B3E3) at a 135-degree angle.

---

## 3. Typography: Editorial Precision
We utilize two typefaces: **Manrope** (Display/Headline) for an authoritative, geometric feel, and **Inter** (Title/Body) for maximum legibility during high-stakes testing.

*   **Display (Manrope):** Use `display-lg` (3.5rem) with `-0.02em` tracking for landing moments. It should feel cinematic and spacious.
*   **Headlines (Manrope):** `headline-md` (1.75rem) should be used to anchor sections. Pair these with significant top-margin to allow the "editorial" feel to breathe.
*   **Body (Inter):** `body-lg` (1rem) is the workhorse. Use `on-surface-variant` (#3e484e) for secondary body text to reduce visual fatigue during long reading sessions.
*   **Labels (Inter):** `label-md` (0.75rem) should always be in All-Caps with `0.05em` letter spacing when used for metadata or technical AI status tags.

---

## 4. Elevation & Depth: Tonal Layering
In this system, "Up" does not mean "Darker Shadow." It means "Lighter Surface."

*   **The Layering Principle:** To lift an element, move it "up" the surface scale. A card containing student data should be `surface-container-lowest` (#ffffff) sitting on a `surface-container-low` (#f3f4f5) background.
*   **Ambient Shadows:** Use shadows only for "floating" elements (modals, dropdowns). 
    *   **Spec:** `0px 12px 32px rgba(0, 45, 91, 0.06)`. Note the use of a Navy tint (`on-secondary-fixed-variant`) instead of pure black to maintain a premium, ambient feel.
*   **Corner Radii:** We utilize a "Soft-Large" approach. 
    *   **Cards:** `xl` (1.5rem)
    *   **Buttons/Inputs:** `DEFAULT` (0.5rem)
    *   **Status Chips:** `full` (9999px)

---

## 5. Components

### Buttons
*   **Primary:** Gradient fill (`primary` to `primary-container`), `on-primary` text. No border. Soft `DEFAULT` (0.5rem) corners.
*   **Secondary:** `secondary-container` (#a7c8ff) background with `on-secondary-container` (#325383) text.
*   **Tertiary:** Ghost style. No background. `primary` text. Hover state uses a subtle `surface-container-high` fill.

### Input Fields
*   **Style:** `surface-container-lowest` fill. 
*   **Border:** `outline-variant` at 20% opacity. 
*   **Focus:** Transition border to `primary` at 100% opacity with a 4px soft "glow" (spread) using `primary-fixed` at 30% opacity.

### AI Proctoring Cards
*   **Rule:** Forbid divider lines between student entries. 
*   **Structure:** Use `md` (0.75rem) spacing between items. Use a `surface-container-low` (#f3f4f5) background on hover to indicate selection.
*   **Status Indicators:** Use `tertiary` (#8c5000) for "Flagged" states—a sophisticated amber that avoids the "panic" of pure red.

### Glass Modals
*   **Style:** `surface-container-lowest` at 80% opacity. 
*   **Blur:** `backdrop-filter: blur(16px)`.
*   **Border:** 1px "Ghost Border" using `outline-variant` at 15% opacity to catch the light.

---

## 6. Do’s and Don’ts

### Do
*   **Do** use extreme whitespace. If a section feels "finished," add 16px more padding.
*   **Do** use tonal shifts (e.g., `surface` to `surface-container-low`) to define dashboard regions.
*   **Do** use `tertiary` colors for AI-driven insights to distinguish them from human-driven actions (`primary`).

### Don’t
*   **Don't** use 1px solid, high-contrast borders. It breaks the "Digital Sanctuary" illusion.
*   **Don't** use pure black (#000000) for text. Use `on-surface` (#191c1d) for high-contrast or `on-surface-variant` for readability.
*   **Don't** use standard "Drop Shadows." If an element doesn't feel "off the page," use a surface color change instead of a shadow.
*   **Don't** crowd the AI proctoring feed. Use the `xl` (1.5rem) corner radius to make each "event" feel like a distinct, contained piece of evidence.