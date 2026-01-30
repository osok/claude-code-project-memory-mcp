# Style Guide: [Application/Brand Name]

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Status | Draft / In Review / Approved |
| Last Updated | YYYY-MM-DD |
| Author(s) | |
| Reviewers | |

---

## 1. Introduction

### 1.1 Purpose

Describe the purpose of this style guide. Explain what applications or products it covers and how it should be used by designers and developers.

### 1.2 Scope

Define what this style guide covers. Explain which platforms, applications, or contexts it applies to and what is excluded.

### 1.3 How to Use This Guide

Explain how designers and developers should use this guide. Describe the relationship between this guide and design tools, code implementations, and other documentation.

### 1.4 Related Documents

Reference related documents that complement this style guide.

| Document | Relationship | Description |
|----------|--------------|-------------|
| UI/UX Design Doc | Applies this guide | Screen and interaction designs |
| Front-End Design Doc | Implements this guide | Technical implementation |
| | | |

---

## 2. Design Principles

### 2.1 Brand Principles

Describe the overarching brand principles that inform visual design. Explain the brand personality and how it is expressed visually.

#### [Principle Name]

**Definition:** Explain what this principle means for the brand.

**Visual Expression:** Describe how this principle manifests in visual design.

*(Repeat for each brand principle)*

### 2.2 Design System Principles

Describe the principles that guide the design system itself. Explain consistency, scalability, and accessibility commitments.

---

## 3. Design Tokens

### 3.1 Token Architecture

Describe how design tokens are organized. Explain the token naming convention, hierarchy, and how tokens are consumed.

### 3.2 Token Naming Convention

Describe the naming convention for design tokens. Explain the pattern and provide examples.

| Pattern | Example | Description |
|---------|---------|-------------|
| | | |

### 3.3 Token Categories

List the categories of design tokens defined in this system.

| Category | Description | Examples |
|----------|-------------|----------|
| Color | | |
| Typography | | |
| Spacing | | |
| Sizing | | |
| Border | | |
| Shadow | | |
| Motion | | |

---

## 4. Color System

### 4.1 Color Philosophy

Describe the approach to color in this design system. Explain how color supports brand identity, usability, and accessibility.

### 4.2 Brand Colors

Define the primary brand colors. Explain their meaning and usage.

#### Primary Color

**Color Name:** [Name]

**Value:** [Hex/RGB/HSL]

**Usage:** Describe when and where this color is used.

**Accessibility:** Describe contrast ratios and accessibility considerations.

*(Repeat for each brand color)*

### 4.3 Color Palette

Define the complete color palette with all shades and tints.

#### [Color Family Name]

| Shade | Token Name | Hex | RGB | Usage |
|-------|------------|-----|-----|-------|
| 50 | | | | |
| 100 | | | | |
| 200 | | | | |
| 300 | | | | |
| 400 | | | | |
| 500 | | | | |
| 600 | | | | |
| 700 | | | | |
| 800 | | | | |
| 900 | | | | |

*(Repeat for each color family)*

### 4.4 Semantic Colors

Define colors by their semantic meaning and usage.

#### Background Colors

| Token | Value | Usage |
|-------|-------|-------|
| background-primary | | Main background |
| background-secondary | | Secondary surfaces |
| background-tertiary | | Tertiary surfaces |
| background-inverse | | Inverted backgrounds |

#### Text Colors

| Token | Value | Usage | Min Contrast |
|-------|-------|-------|--------------|
| text-primary | | Primary text | |
| text-secondary | | Secondary text | |
| text-disabled | | Disabled text | |
| text-inverse | | Text on dark backgrounds | |
| text-link | | Hyperlinks | |

#### Border Colors

| Token | Value | Usage |
|-------|-------|-------|
| border-default | | Standard borders |
| border-strong | | Emphasized borders |
| border-subtle | | Subtle dividers |

#### Interactive Colors

| Token | Value | Usage |
|-------|-------|-------|
| interactive-primary | | Primary actions |
| interactive-primary-hover | | Primary hover state |
| interactive-primary-active | | Primary active state |
| interactive-secondary | | Secondary actions |
| interactive-disabled | | Disabled state |

#### Feedback Colors

| Token | Value | Usage |
|-------|-------|-------|
| feedback-success | | Success messages |
| feedback-warning | | Warning messages |
| feedback-error | | Error messages |
| feedback-info | | Informational messages |

### 4.5 Color Accessibility

Describe color accessibility requirements. Explain contrast ratios, color blindness considerations, and testing methods.

| Combination | Contrast Ratio | WCAG Level |
|-------------|----------------|------------|
| text-primary on background-primary | | |
| text-secondary on background-primary | | |
| interactive-primary on background-primary | | |

### 4.6 Dark Mode Colors

Define color mappings for dark mode if supported.

| Light Mode Token | Dark Mode Value | Notes |
|------------------|-----------------|-------|
| | | |

---

## 5. Typography

### 5.1 Typography Philosophy

Describe the approach to typography. Explain how type supports readability, hierarchy, and brand expression.

### 5.2 Font Families

Define the font families used in the design system.

#### Primary Font

**Font Name:** [Name]

**Weights Available:** [List weights]

**Usage:** Describe where this font is used.

**Fallback Stack:** Describe fallback fonts.

**Licensing:** Describe licensing requirements.

#### Secondary Font

**Font Name:** [Name]

**Weights Available:** [List weights]

**Usage:** Describe where this font is used.

**Fallback Stack:** Describe fallback fonts.

#### Monospace Font

**Font Name:** [Name]

**Usage:** Describe where this font is used (code, data).

### 5.3 Type Scale

Define the typographic scale used for sizing.

| Token | Size (px) | Size (rem) | Line Height | Usage |
|-------|-----------|------------|-------------|-------|
| text-xs | | | | |
| text-sm | | | | |
| text-base | | | | |
| text-lg | | | | |
| text-xl | | | | |
| text-2xl | | | | |
| text-3xl | | | | |
| text-4xl | | | | |

### 5.4 Type Styles

Define the complete type styles combining font, size, weight, and other properties.

#### Headings

| Style | Font | Size | Weight | Line Height | Letter Spacing | Usage |
|-------|------|------|--------|-------------|----------------|-------|
| heading-1 | | | | | | Page titles |
| heading-2 | | | | | | Section headings |
| heading-3 | | | | | | Subsection headings |
| heading-4 | | | | | | Card headings |
| heading-5 | | | | | | |
| heading-6 | | | | | | |

#### Body Text

| Style | Font | Size | Weight | Line Height | Letter Spacing | Usage |
|-------|------|------|--------|-------------|----------------|-------|
| body-large | | | | | | Lead paragraphs |
| body-default | | | | | | Standard body text |
| body-small | | | | | | Secondary text |

#### UI Text

| Style | Font | Size | Weight | Line Height | Letter Spacing | Usage |
|-------|------|------|--------|-------------|----------------|-------|
| label | | | | | | Form labels |
| button | | | | | | Button text |
| caption | | | | | | Captions, hints |
| overline | | | | | | Overline text |

### 5.5 Responsive Typography

Describe how typography scales across breakpoints.

| Style | Mobile | Tablet | Desktop |
|-------|--------|--------|---------|
| heading-1 | | | |
| heading-2 | | | |
| body-default | | | |

### 5.6 Typography Guidelines

Describe guidelines for using typography effectively.

#### Line Length

Describe optimal line length for readability. Explain character count targets.

#### Paragraph Spacing

Describe spacing between paragraphs and text blocks.

#### Text Alignment

Describe when to use different text alignments.

#### Text Truncation

Describe how to handle text overflow and truncation.

---

## 6. Spacing System

### 6.1 Spacing Philosophy

Describe the approach to spacing. Explain how consistent spacing creates visual rhythm and hierarchy.

### 6.2 Spacing Scale

Define the spacing scale used throughout the design system.

| Token | Value (px) | Value (rem) | Usage |
|-------|------------|-------------|-------|
| space-0 | 0 | 0 | |
| space-1 | | | Tight spacing |
| space-2 | | | |
| space-3 | | | |
| space-4 | | | Default spacing |
| space-5 | | | |
| space-6 | | | |
| space-8 | | | |
| space-10 | | | |
| space-12 | | | Section spacing |
| space-16 | | | |
| space-20 | | | Large gaps |
| space-24 | | | |

### 6.3 Spacing Applications

Describe how spacing is applied in different contexts.

#### Component Internal Spacing

Describe spacing within components (padding).

| Context | Horizontal | Vertical |
|---------|------------|----------|
| Button (small) | | |
| Button (default) | | |
| Button (large) | | |
| Card | | |
| Input | | |

#### Component External Spacing

Describe spacing between components (margin, gap).

| Context | Spacing |
|---------|---------|
| Form fields | |
| Card grid | |
| Section gap | |

### 6.4 Layout Spacing

Describe spacing for page-level layout.

| Element | Value | Notes |
|---------|-------|-------|
| Page margin (mobile) | | |
| Page margin (tablet) | | |
| Page margin (desktop) | | |
| Section spacing | | |
| Content max-width | | |

---

## 7. Grid System

### 7.1 Grid Philosophy

Describe the approach to grid-based layout. Explain how the grid creates consistency and flexibility.

### 7.2 Grid Configuration

Define the grid configuration for each breakpoint.

| Breakpoint | Columns | Gutter | Margin | Max Width |
|------------|---------|--------|--------|-----------|
| Mobile (<768px) | | | | |
| Tablet (768-1024px) | | | | |
| Desktop (1024-1440px) | | | | |
| Large (>1440px) | | | | |

### 7.3 Column Spans

Describe common column span patterns for content layout.

| Pattern | Mobile | Tablet | Desktop | Usage |
|---------|--------|--------|---------|-------|
| Full width | | | | |
| Half | | | | |
| Third | | | | |
| Quarter | | | | |
| Sidebar + Content | | | | |

### 7.4 Grid Usage Guidelines

Describe guidelines for using the grid effectively. Explain when to break the grid and how to handle edge cases.

---

## 8. Iconography

### 8.1 Icon Philosophy

Describe the approach to iconography. Explain the icon style, its relationship to the brand, and guiding principles.

### 8.2 Icon Specifications

Define the technical specifications for icons.

| Property | Value | Notes |
|----------|-------|-------|
| Grid size | | Base artboard size |
| Stroke width | | For outlined icons |
| Corner radius | | For rounded corners |
| Optical sizes | | Different sizes available |

### 8.3 Icon Sizes

Define the standard icon sizes.

| Token | Size (px) | Usage |
|-------|-----------|-------|
| icon-xs | | Inline with small text |
| icon-sm | | Inline with body text |
| icon-md | | Buttons, inputs |
| icon-lg | | Feature icons |
| icon-xl | | Hero icons |

### 8.4 Icon Colors

Describe how icons are colored.

| Context | Color Token | Notes |
|---------|-------------|-------|
| Default | | |
| Interactive | | |
| Disabled | | |
| Success | | |
| Error | | |

### 8.5 Icon Library

Describe the icon library used. Explain where icons are sourced, how custom icons are created, and how to request new icons.

### 8.6 Icon Usage Guidelines

Describe guidelines for using icons effectively. Explain when to use icons, pairing with labels, and accessibility requirements.

---

## 9. Imagery and Illustration

### 9.1 Photography Style

Describe the photography style guidelines. Explain subject matter, composition, lighting, and color treatment.

#### Subject Matter

Describe appropriate subjects for photography.

#### Composition

Describe composition guidelines.

#### Color Treatment

Describe any color grading or treatment applied to photos.

### 9.2 Illustration Style

Describe the illustration style guidelines if illustrations are used.

#### Style Characteristics

Describe the visual characteristics of illustrations.

#### Color Usage

Describe how colors are used in illustrations.

#### Composition

Describe composition guidelines for illustrations.

### 9.3 Image Specifications

Define technical specifications for images.

| Context | Aspect Ratio | Min Resolution | Format |
|---------|--------------|----------------|--------|
| Hero image | | | |
| Card thumbnail | | | |
| Avatar | | | |
| Product image | | | |

### 9.4 Image Accessibility

Describe accessibility requirements for images. Explain alt text guidelines and decorative image handling.

---

## 10. Borders and Dividers

### 10.1 Border Radius

Define the border radius scale.

| Token | Value | Usage |
|-------|-------|-------|
| radius-none | 0 | Sharp corners |
| radius-sm | | Subtle rounding |
| radius-md | | Default rounding |
| radius-lg | | Prominent rounding |
| radius-xl | | Very rounded |
| radius-full | 9999px | Pills, circles |

### 10.2 Border Widths

Define border width values.

| Token | Value | Usage |
|-------|-------|-------|
| border-none | 0 | |
| border-thin | | Subtle borders |
| border-default | | Standard borders |
| border-thick | | Emphasized borders |

### 10.3 Border Styles

Describe when to use different border styles.

| Style | Usage |
|-------|-------|
| Solid | |
| Dashed | |
| None | |

### 10.4 Dividers

Describe divider patterns and usage.

| Divider Type | Thickness | Color | Usage |
|--------------|-----------|-------|-------|
| Horizontal | | | |
| Vertical | | | |

---

## 11. Shadows and Elevation

### 11.1 Elevation Philosophy

Describe the approach to elevation and shadows. Explain how shadows communicate hierarchy and interactivity.

### 11.2 Shadow Scale

Define the shadow scale.

| Token | Value | Elevation | Usage |
|-------|-------|-----------|-------|
| shadow-none | none | 0 | Flat elements |
| shadow-sm | | 1 | Subtle lift |
| shadow-md | | 2 | Cards, dropdowns |
| shadow-lg | | 3 | Modals, popovers |
| shadow-xl | | 4 | Dialogs |

### 11.3 Elevation Levels

Describe the elevation system and what appears at each level.

| Level | Shadow | Components |
|-------|--------|------------|
| 0 (Base) | | Page background |
| 1 | | Cards, sections |
| 2 | | Dropdowns, tooltips |
| 3 | | Modals, dialogs |
| 4 | | Notifications |

### 11.4 Shadow Usage Guidelines

Describe guidelines for using shadows effectively. Explain when shadows are appropriate and when to avoid them.

---

## 12. Motion and Animation

### 12.1 Motion Philosophy

Describe the approach to motion and animation. Explain how motion supports usability and brand expression.

### 12.2 Duration Scale

Define the duration scale for animations.

| Token | Duration | Usage |
|-------|----------|-------|
| duration-instant | 0ms | Immediate feedback |
| duration-fast | | Micro-interactions |
| duration-normal | | Standard transitions |
| duration-slow | | Complex animations |
| duration-slower | | Page transitions |

### 12.3 Easing Functions

Define the easing functions used.

| Token | Value | Usage |
|-------|-------|-------|
| ease-linear | | Progress indicators |
| ease-in | | Elements exiting |
| ease-out | | Elements entering |
| ease-in-out | | Elements moving |
| ease-spring | | Playful interactions |

### 12.4 Standard Transitions

Define standard transition patterns.

| Transition | Properties | Duration | Easing | Usage |
|------------|------------|----------|--------|-------|
| transition-colors | | | | Hover states |
| transition-transform | | | | Scale, move |
| transition-opacity | | | | Fade in/out |
| transition-all | | | | Multiple properties |

### 12.5 Animation Patterns

Describe common animation patterns.

#### Enter Animations

| Animation | Description | Duration | Easing |
|-----------|-------------|----------|--------|
| fade-in | | | |
| slide-in-up | | | |
| scale-in | | | |

#### Exit Animations

| Animation | Description | Duration | Easing |
|-----------|-------------|----------|--------|
| fade-out | | | |
| slide-out-down | | | |
| scale-out | | | |

### 12.6 Reduced Motion

Describe how animations adapt for users who prefer reduced motion. Explain what is modified or disabled.

---

## 13. Theming

### 13.1 Theme Architecture

Describe how theming is structured. Explain the relationship between base tokens and theme-specific values.

### 13.2 Light Theme

Define the light theme token values.

| Token | Value | Notes |
|-------|-------|-------|
| | | |

### 13.3 Dark Theme

Define the dark theme token values.

| Token | Value | Notes |
|-------|-------|-------|
| | | |

### 13.4 Theme Switching

Describe how theme switching works. Explain user preferences, system detection, and persistence.

### 13.5 Creating Custom Themes

Describe how to create custom themes. Explain which tokens can be customized and any constraints.

---

## 14. Accessibility Standards

### 14.1 Accessibility Commitment

Describe the accessibility standards this design system commits to meeting.

| Standard | Level | Notes |
|----------|-------|-------|
| WCAG | 2.1 AA / 2.1 AAA | |

### 14.2 Color Accessibility

Summarize color accessibility requirements and how this guide meets them.

### 14.3 Typography Accessibility

Summarize typography accessibility requirements and how this guide meets them.

### 14.4 Motion Accessibility

Summarize motion accessibility requirements and how this guide meets them.

### 14.5 Testing Requirements

Describe accessibility testing requirements. Explain tools and methods for verifying compliance.

---

## 15. Implementation Reference

### 15.1 Design Tool Resources

List design tool resources implementing this style guide.

| Resource | Tool | Location | Contents |
|----------|------|----------|----------|
| Component Library | Figma/Sketch | | |
| Token Library | | | |
| Icon Library | | | |

### 15.2 Code Implementation

Describe how this style guide is implemented in code.

| Implementation | Technology | Location | Notes |
|----------------|------------|----------|-------|
| CSS Variables | | | |
| Design Tokens | | | |
| Component Library | | | |

### 15.3 Token Export Formats

Describe available token export formats.

| Format | Usage | Location |
|--------|-------|----------|
| CSS Custom Properties | | |
| JSON | | |
| SCSS Variables | | |
| JavaScript | | |

---

## 16. Versioning and Changelog

### 16.1 Version History

Track changes to this style guide.

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| | | | |

### 16.2 Deprecation Policy

Describe how deprecated tokens or styles are handled. Explain the deprecation timeline and migration process.

### 16.3 Breaking Changes

Describe how breaking changes are communicated and managed.

---

## 17. Glossary

Define terms, acronyms, and concepts used in this document.

| Term | Definition |
|------|------------|
| Design Token | |
| Semantic Color | |
| | |

---

## Appendix A: Quick Reference

### A.1 Color Quick Reference

Quick reference for commonly used colors.

### A.2 Typography Quick Reference

Quick reference for commonly used type styles.

### A.3 Spacing Quick Reference

Quick reference for commonly used spacing values.

---

## Appendix B: Brand Assets

### B.1 Logo Usage

Describe logo usage guidelines and provide references.

### B.2 Brand Colors

Summarize primary brand colors.

### B.3 Brand Fonts

Summarize brand typography.

---

## Appendix C: Reference Documents

| Document | Version | Relevance |
|----------|---------|-----------|
| | | |
