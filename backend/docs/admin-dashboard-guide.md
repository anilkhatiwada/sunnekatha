# SunneKatha Admin Dashboard Guide

This guide is for editors, publishers, audio managers, playlist curators,
copyright staff, support staff, and analytics viewers. It explains the everyday
editorial workflow without requiring technical knowledge.

The options you see depend on your staff role. If a page or action mentioned in
this guide is missing, ask a Super Administrator to check your role. Do not ask
for a broader role than your work requires.

## 1. Dashboard overview

Open the SunneKatha administration address supplied by your administrator and
sign in with your individual staff account. Do not share accounts.

The dashboard shows summary cards for content, processing, users, subscriptions,
reviews, and listening activity. Selecting a card opens the corresponding
filtered list. The tables below the cards highlight recent activity and work
requiring attention, such as:

- tracks with processing or review problems;
- recent uploads and publications;
- failed processing jobs;
- pending reviews;
- scheduled publications;
- popular tracks, authors, and narrators.

Use the sidebar to move between areas. On a tablet or smaller laptop, open the
sidebar with the menu button. Sidebar sections can be collapsed.

The environment label identifies where you are working:

- **LOCAL** is a developer environment.
- **STAGING** is for testing and review.
- **PRODUCTION** contains the live service.

Always check the environment label before publishing, changing subscriptions, or
running a bulk action.

## 2. Staff roles

SunneKatha uses the following roles:

| Role | Main responsibilities |
| --- | --- |
| Super Administrator | System administration and access to all staff tools |
| Publisher | Editorial review, scheduling, publication, playlists, and homepage management |
| Senior Editor | Content editing, review, playlists, and homepage management |
| Editor | Creating and editing content and homepage sections |
| Audio Manager | Upload review, audio processing, and processing retries |
| Playlist Curator | Creating, ordering, and publishing playlists |
| Copyright Manager | Rights holders, licenses, documents, and verification |
| Support Staff | User accounts and subscription administration |
| Analytics Viewer | Aggregate listening analytics and authorized CSV export |

Roles are additive: a staff member may have more than one. Only actual Django
superusers can change group permissions or grant administrative access.

## 3. Creating an author

1. Open **Content → Authors**.
2. Select **Add author**.
3. Enter the Nepali name. Add the English name when available.
4. Add Nepali and English biographies using verified editorial material.
5. Upload an approved profile image.
6. Add birth date, death date, and country only when known.
7. Leave **Featured** off unless the author has been selected for promotion.
8. Use **Verified** only after the identity has been editorially confirmed.
9. Save the author.

The slug is generated automatically. Before saving, check the similar-name
warning to avoid creating a duplicate author. After saving, use the related-work
and related-track links to review connected content.

## 4. Creating a narrator

1. Open **Content → Narrators**.
2. Select **Add narrator**.
3. Enter the Nepali name and, when available, the English name.
4. Add the approved biographies and profile image.
5. Link a user account only when the narrator has an approved SunneKatha
   account.
6. Set **Featured** and **Verified** only as part of an editorial decision.
7. Save the narrator.

The narrator page shows related tracks and follower information. Authorized
staff can preview the most recent available narration. The preview requests a
short-lived media link only after play is selected.

## 5. Creating a literary work

Create the author, language, genre, and mood records first.

1. Open **Content → Literary Works**.
2. Select **Add literary work**.
3. In **Basic Information**, enter the Nepali title and any English title,
   subtitles, and content type.
4. In **Author and Classification**, select the author, language, genres, moods,
   and publication year.
5. Add the Nepali and English descriptions.
6. In **Copyright and Rights**, record the copyright status, stored copyright
   owner, and license notes. Do not guess a legal status.
7. Upload approved cover artwork.
8. Save the work as an unpublished record.

The slug is generated automatically. After saving, use the related-track link to
create or review its audio tracks. Publishing the literary work does not
automatically publish its tracks.

## 6. Uploading audio

Audio is uploaded through the approved creator or direct-upload workflow. The
browser sends the file directly to private storage; Django Admin does not receive
or proxy the audio bytes.

1. In the creator upload flow, select **Audio master**.
2. Choose the approved master file and confirm its filename, type, and expected
   size.
3. Complete the upload before the upload session expires.
4. Confirm the upload in the creator flow.
5. In Admin, open **Audio Operations → Upload Sessions**.
6. Find the upload by filename or uploader.
7. Check the expected size, actual size, content type, status, and expiry.
8. Use **Verify selected uploads** if verification is still required.
9. Link or open the related track when available.
10. Use **Start processing selected audio uploads** only when the session is
    confirmed and a related failed track is eligible.

Never copy an S3 key, presigned URL, or AWS credential into editorial notes.
Those values are intentionally hidden from Admin.

## 7. Reviewing processing

Open **Content → Audio Tracks** or **Audio Operations → Processing Queue**.

Processing moves through the following operational states:

- **Draft** — track metadata is being prepared;
- **Uploaded** — the source upload is confirmed;
- **Queued** — processing is waiting to begin;
- **Processing** — audio work is in progress;
- **Ready** — processed audio is available for review;
- **Failed** — processing needs attention;
- **Published** — the ready track is publicly published.

Open the track and review:

- the processing badge and processing stage;
- low- and high-quality file availability;
- duration and audio metadata;
- the safe audio preview;
- the editor-facing error summary when processing failed.

Do not publish a track until processing is **Ready**. Ordinary editors see only
the safe error summary. Expanded technical details are restricted to
superusers.

## 8. Publishing a track

Track review follows this sequence:

**Draft → Submitted → Approved → Scheduled or Published**

**Changes Requested**, **Rejected**, and **Archived** are used when appropriate.

1. Open **Content → Audio Tracks**.
2. Confirm the work, author, narrator, language, title, description, artwork,
   rights information, premium status, and explicit-content status.
3. Play each available audio quality. Do not rely only on the filename.
4. Confirm processing is **Ready**.
5. Use **Submit selected for review**.
6. An editor with approval permission opens the pending review and checks all
   attention warnings.
7. The editor selects **Approve selected**, or requests changes with a reason.
8. A Publisher selects **Publish selected** and confirms the action, or schedules
   it for later.

The system blocks publication when mandatory processing or copyright
requirements are unresolved. Creators cannot approve their own submissions
unless they have the explicit exceptional permission.

## 9. Creating an album

1. Open **Content → Albums**.
2. Select **Add album**.
3. Enter the Nepali and English titles, album type, author, and descriptions.
4. Add genres, moods, release date, and approved cover artwork.
5. Save the album as unpublished.
6. Add or link tracks in stable track order.
7. Check the calculated track count and total duration.
8. Use the play-all preview to review available tracks.
9. Publish only after the album metadata and included tracks are ready.

For a very large album, use the related-track list instead of attempting to edit
every track inline. **Duplicate** creates an unpublished metadata copy and does
not duplicate durable track records.

## 10. Creating a playlist

1. Open **Editorial → Playlists**.
2. Select **Add playlist**.
3. Enter the Nepali and English titles, descriptions, and cover image.
4. Select the playlist type and visibility.
5. Save the playlist before managing its ordered tracks.
6. Search for tracks, add them, and set their integer positions.
7. Use drag-and-drop where available, or edit position numbers as the keyboard
   fallback.
8. Save and check the confirmation message.
9. Use **Play playlist preview** to review the sequence.
10. Publish only when every track is published, processing-ready, and available.

Only staff can create editorial playlists. **Private** playlists are owner-only,
**Unlisted** playlists work by direct link, and **Public** playlists appear in
listings. Use **Recalculate positions** if ordering becomes inconsistent, and
**Remove unavailable tracks** after reviewing what will be removed.

## 11. Managing homepage sections

1. Open **Editorial → Homepage Sections**.
2. Select **Add homepage section**.
3. Enter the stable identifier and Nepali and English display titles.
4. Choose the section type.
5. Set its position among other sections.
6. Add linked items that match the section type.
7. Order items with drag-and-drop or position numbers.
8. Set start and end times for seasonal or scheduled sections.
9. Save and use the homepage preview.
10. Activate the section when it is ready.

The system rejects incompatible item types and duplicate positions. Upcoming
sections do not appear before their start time, and expired sections are hidden
from public responses. Deactivation requires confirmation.

## 12. Reviewing copyright permissions

Open **Rights → Copyright Licenses** and **Rights → Permission Documents**.

For each literary work, review the stored:

- copyright status;
- rights holder;
- permission type;
- effective and expiration dates;
- territory;
- audio and monetization permissions;
- document availability;
- verification status.

The admin records information and workflow status; it does not make legal
conclusions. If ownership is unclear, leave it marked as unclear and escalate it
to the Copyright Manager.

Permission documents are private. Use **Download securely** or **Preview
securely**; never attempt to find a raw storage URL. Verify a document only after
checking that it belongs to the correct work and rights holder and that its
dates and permissions match the stored record. Revoking verification requires
confirmation and creates an audit entry.

## 13. Scheduling publication

1. Ensure the track is **Approved**, processing is **Ready**, and required rights
   are resolved.
2. Open **Editorial → Scheduled Publications** or use the track’s **Schedule**
   action.
3. Enter a future date and time in the configured admin timezone.
4. Confirm the schedule.
5. Review the item under **Today**, **Tomorrow**, **This week**, or **Later**.

Authorized Publishers can reschedule, cancel a schedule, or publish now. The
system prevents scheduling content that is unready or has unresolved required
permissions.

## 14. Managing subscriptions

Open **Audience → Subscriptions**.

The list shows the user, plan, status, start date, trial end, renewal,
expiration, cancellation, and current access status. Authorized Support Staff
can:

- grant temporary premium access;
- extend a subscription;
- cancel a subscription;
- revoke access immediately;
- restore manually revoked access.

Every manual change requires confirmation and a reason. It records the staff
member, timestamp, before state, and after state. Manual actions do not imitate
events from an external billing provider and do not overwrite provider-owned
data.

## 15. Reading analytics

Open **System → Analytics Dashboard**.

Choose **Today**, **Last 7 days**, **Last 30 days**, **Current month**, or a
custom date range. The dashboard shows aggregate listening hours, plays, unique
listeners, completion rate, popular content, new users, and premium conversions
where data is available.

Analytics may be delayed because it is calculated periodically. Read any delay
or incomplete-data note before sharing figures. The dashboard intentionally
avoids exposing individual listening histories. CSV export appears only for
authorized analytics roles.

## 16. Handling failed processing

1. Open **Audio Operations → Failed Processing**.
2. Filter by failed stage, date, or creator, or search by track title or
   filename.
3. Review the safe error summary, stage, attempt count, last attempt, related
   upload, and related track.
4. Correct metadata, upload, or rights problems before retrying.
5. Select one or more eligible jobs and choose **Retry**.
6. Review the confirmation page and confirm.
7. Return to the processing queue and check that the job moves to **Queued** or
   **Processing**.

The system prevents a duplicate retry when a job is already active and records
who requested the retry. If retries are exhausted, escalate to an Audio Manager
or administrator rather than repeatedly changing the record.

## 17. Safe bulk actions

Bulk actions affect every selected row. Before running one:

1. Apply filters first.
2. Read the result count.
3. Select only the intended rows.
4. Read the confirmation page and warning.
5. Confirm the environment label.
6. Confirm the action once.
7. Read both success and partial-failure messages.

Sensitive actions such as suspension, unpublication, archiving, processing
retry, upload cancellation or abandonment, verification revocation, temporary
object deletion, subscription changes, and homepage deactivation require
confirmation.

The service validates every item again when the action runs. A partial-failure
message is not permission to ignore the skipped items; open each failure and
resolve its stated reason. CSV exports contain approved metadata fields only and
do not include audio paths, transcripts, credentials, or signed URLs.

## 18. Troubleshooting

### I cannot see a menu item or action

Your role probably does not include that permission. Ask a Super Administrator
to confirm your assigned role. Do not use another person’s account.

### My form will not save

Read the message beside each highlighted field. Common causes include a missing
required relationship, duplicate slug or position, incompatible homepage item,
invalid publication state, or an expired rights date.

### A track cannot be submitted, approved, scheduled, or published

Check that processing is **Ready**, the review state allows the requested next
step, required metadata is complete, and copyright requirements are resolved.
Open **Pending Reviews** to see attention warnings.

### An upload is missing or expired

Search **Upload Sessions** by filename and uploader. If the session expired, the
uploader must request a new upload session. Never reuse or manually edit an
object key.

### Audio preview is unavailable

Confirm that the requested quality exists and that you have permission to view
the track or upload. Reload the page and try again. Preview links are created
only when requested and expire quickly.

### Processing retry did not start

The job may already be active, may not be in a failed state, or may have reached
its attempt limit. Review the failed-processing page and escalate when the retry
is unavailable.

### I received a CSRF or “Forbidden” message

Reload the form, ensure cookies are enabled, and sign in again if necessary.
Do not submit an old form from a restored browser tab. If the problem continues,
send the administrator the environment label, page address, and time of the
error—never send your password or a signed URL.

### A bulk action changed only some records

Read the partial-failure message. SunneKatha validates records individually, so
ineligible or unauthorized rows remain unchanged. Correct those rows and run a
new, narrowly selected action.

### I made the wrong change

Stop before making compensating edits. Record what happened and contact the
appropriate Publisher or Super Administrator. Important actions are stored in
the administrative audit log and can be reviewed safely.
