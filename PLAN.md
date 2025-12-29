# Email System Enhancement Plan

## Overview

This plan covers two main objectives:
1. **Style all emails for light and dark mode compatibility**
2. **Add new email types relevant to the comic book pull-list domain**

---

## Part 1: Email Template Architecture Refactor

### Current State
- 3 email functions with inline HTML templates in `app/services/email.py`
- Duplicated boilerplate (headers, footers, button styles)
- Light mode only (hardcoded light backgrounds)
- Two color themes: purple (auth) and gold/amber (notifications)

### Proposed Architecture

#### 1.1 Create Email Template System

Create `app/templates/email/` directory with Jinja2 templates:

```
app/templates/email/
├── base.html           # Shared layout with dark mode support
├── base.txt            # Plain text base template
├── magic_link.html
├── magic_link.txt
├── password_reset.html
├── password_reset.txt
├── pulllist_ready.html
├── pulllist_ready.txt
├── reading_reminder.html
├── reading_reminder.txt
├── weekly_digest.html
├── weekly_digest.txt
└── welcome.html
└── welcome.txt
```

#### 1.2 Dark Mode Implementation Strategy

Email dark mode support varies by client. The approach:

1. **Use `@media (prefers-color-scheme: dark)` in `<style>` block** - works in Apple Mail, iOS Mail, Outlook (macOS)
2. **Add `data-ogsc` and `data-ogsb` attributes** - Outlook.com dark mode targeting
3. **Use `[data-ogsc]` selectors** - Gmail dark mode (partial)
4. **Maintain readable fallback colors** - for clients that strip styles

**Base template will include:**
```html
<style>
  @media (prefers-color-scheme: dark) {
    .email-body { background-color: #1a1a2e !important; }
    .email-content { background-color: #16213e !important; }
    .email-text { color: #e8e8e8 !important; }
    .email-text-muted { color: #a0a0a0 !important; }
  }
</style>
```

**Color palette for dark mode:**
- Background: `#1a1a2e` (dark blue-gray)
- Content area: `#16213e` (slightly lighter)
- Text: `#e8e8e8` (off-white)
- Muted text: `#a0a0a0`
- Links: Keep brand colors (purple/gold) - they work in both modes

#### 1.3 Refactor `email.py`

- Create `render_email_template(template_name, context)` helper
- Create `send_email(to, subject, template_name, context)` generic function
- Reduce duplication of SMTP sending logic
- Keep individual `send_X_email()` functions as thin wrappers

---

## Part 2: New Email Types

### Recommended Emails for Wednesday

#### 2.1 Welcome Email (High Priority)
**Trigger:** After user account creation
**Content:**
- Welcome message
- Quick start guide (how to track series)
- Link to dashboard
- Link to settings to configure notifications

#### 2.2 Reading Reminder (Medium Priority)
**Trigger:** Configurable - e.g., Saturday if unread comics exist
**Content:**
- Count of unread comics from current week
- List of unread titles
- "Catch up before next Wednesday!" CTA
**Requirements:**
- New setting: `READING_REMINDER_ENABLED` and `READING_REMINDER_DAY`
- Track read status per book (may already exist via Komga)
- New scheduler job

#### 2.3 Weekly Digest (Medium Priority)
**Trigger:** End of week (Tuesday) or configurable
**Content:**
- Summary of week: X comics released, Y read, Z unread
- Reading stats/progress
- Preview of upcoming releases (if Mylar data available)
**Requirements:**
- Aggregate WeeklyBook data with read status
- New scheduler job

#### 2.4 Series Milestone (Low Priority)
**Trigger:** When a tracked series reaches milestone (issue #50, #100, etc.)
**Content:**
- Celebration message
- Series stats (how long you've been tracking, issues read)
**Requirements:**
- Track issue numbers, detect milestones
- New notification preference

#### 2.5 Connection Alert (Low Priority)
**Trigger:** When Komga or Mylar connection fails
**Content:**
- Alert that integration is down
- Instructions to check settings
**Requirements:**
- Health check system
- Admin notification preference

---

## Part 3: Implementation Steps

### Phase 1: Template Infrastructure
1. Create `app/templates/email/` directory
2. Create `base.html` with dark mode CSS and shared layout
3. Create `base.txt` for plain text emails
4. Create `app/services/email_templates.py` with template rendering helpers
5. Refactor `email.py` to use new template system
6. Migrate existing 3 emails to new templates
7. Test in multiple email clients (Apple Mail, Gmail, Outlook)

### Phase 2: Welcome Email
1. Add `send_welcome_email()` function
2. Create welcome email templates
3. Call from user registration flow
4. Add tests

### Phase 3: Reading Reminder
1. Add configuration settings for reading reminders
2. Create reading reminder templates
3. Add scheduler job for reminders
4. Query Komga for read status or track locally
5. Add user preference for enabling/disabling
6. Add tests

### Phase 4: Weekly Digest
1. Add configuration settings
2. Create digest email templates
3. Add scheduler job
4. Aggregate weekly stats
5. Add tests

---

## Design Specifications

### Color Themes

**Authentication Emails (Purple):**
- Light: `#667eea → #764ba2` gradient
- Dark: Same gradient (works well on dark backgrounds)

**Notification Emails (Gold/Amber):**
- Light: `#FCD34D → #F59E0B` gradient
- Dark: Same gradient

**Reminder/Digest Emails (suggest Blue/Teal):**
- Light: `#06B6D4 → #0891B2` gradient
- Dark: Same gradient

### Typography
- Font stack: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif`
- Body text: 16px
- Headings: 28px (h1), 20px (h2)
- Muted text: 14px, 12px for footer

### Spacing
- Email max-width: 600px
- Header padding: 30px
- Content padding: 30px
- Button padding: 15px 40px

---

## Files to Create/Modify

**New Files:**
- `app/templates/email/base.html`
- `app/templates/email/base.txt`
- `app/templates/email/magic_link.html`
- `app/templates/email/magic_link.txt`
- `app/templates/email/password_reset.html`
- `app/templates/email/password_reset.txt`
- `app/templates/email/pulllist_ready.html`
- `app/templates/email/pulllist_ready.txt`
- `app/templates/email/welcome.html`
- `app/templates/email/welcome.txt`
- `app/templates/email/reading_reminder.html`
- `app/templates/email/reading_reminder.txt`
- `app/templates/email/weekly_digest.html`
- `app/templates/email/weekly_digest.txt`
- `app/services/email_templates.py`

**Modified Files:**
- `app/services/email.py` - refactor to use templates
- `app/config.py` - add new email settings
- `app/scheduler.py` - add reminder/digest jobs
- `app/main.py` - call welcome email on registration

---

## Questions for User

1. **Reading Reminder Day:** What day should reading reminders be sent? (Saturday suggested - gives weekend to catch up)

2. **Digest Timing:** Weekly digest on Tuesday (end of comic week) or another day?

3. **Welcome Email:** Should this be sent on account creation, or only after first login?

4. **Additional Emails:** Any other email types you'd like beyond the ones listed?
