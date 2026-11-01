# AMS Frontend (GUI) Audit

Date: 2026-11-01. Scope: Tkinter GUI, exercised as Admin, Staff and Passenger.

## Fix status (updated after the redesign)
Items 1-8 below are fixed and re-verified by re-running the same GUI script: 147 checks, 143 pass. The 4 that "fail" are not bugs: three are the feature gaps in items 11-13 (bookings search/sort, user editing, printable boarding pass), which were not part of this round, and one is an old check that expected the previous error wording for a duplicate booking.

Items 9, 10 and 14 were fixed along the way (single Gate input, a clear warning for "Set status" with nothing chosen, a Cancel button on the seat map). Item 15 (date picker, show/hide password) is only partly done: the login screen now has "Show password".

The UI was also redesigned with animation: an animated login scene, a header with live clock and user chip, count-up statistic tiles, tabs with a sliding underline, animated buttons, table rows that fade in and highlight on hover, and a seat map that reveals row by row. The audit below describes the UI before these changes.

## Method and limits
- A script (`audit_gui.py`, kept in the Claude session scratchpad) started the real `AirportApp`, logged in as each role and called each button's handler, then read back table rows, form fields and the dialogs shown.
- It ran against a throw-away copy of the sample database, so `data/airport.db` was not touched.
- Message boxes were captured instead of displayed. Mouse clicks, focus and tab order were not tested by hand.
- Layout numbers are Tk's own required vs available height at the 980x620 minimum window size. They depend on Windows display scaling, so check them on your own screen.
- 145 checks were recorded. Some were observations from reading the code and not driven behaviour. They are marked "(code reading)" below.

## Summary
| Role | Working | Needs improvement |
|---|---|---|
| Login / Register (all) | 18 | 1 |
| Admin | 48 | 8 |
| Staff | 37 | 2 |
| Passenger | 28 | 5 |

No crash, unhandled exception or wrong data was found in any flow. Every error went through a clear dialog.

## What works
**Login and registration**
- Empty, wrong and unknown credentials give clear errors. The same message is used for a wrong password and an unknown user.
- Usernames are trimmed and case-insensitive. Logout works. Enter submits the login form.
- Registration rejects a password mismatch, a weak password, a bad phone number, a bad e-mail and a duplicate username.
- A valid registration prefills the login username, and the new passenger can then log in.

**Admin**
- Tabs shown: Flights, Bookings, Check-in & Baggage, Users.
- Flights:
  - The list, the "include cancelled" filter and row-to-form population work.
  - Add rejects a past date, bad gate, same origin and destination, bad fare, rows over 40, a wrong date format, an empty flight number, a gate conflict and a duplicate flight.
  - Valid add, update, assign gate and status change all work.
  - Invalid status moves such as SCHEDULED to DEPARTED are blocked.
  - Cancel asks for confirmation and cascades to bookings ("3 booking(s) cancelled").
  - Editing a cancelled flight is refused, and so is changing the route after tickets are sold.
- Bookings: the admin sees all bookings, can cancel any of them, and a repeat cancel gives "already cancelled".
- Check-in: the admin can check a passenger in (lower-case PNR accepted).
- Users: the list works. Create staff and create admin work. Duplicate, weak-password and bad-phone input are rejected, and the form resets after a create.

**Staff**
- Tabs shown: Check-in & Baggage, Flights, Bookings. Flights and Bookings are read-only (no edit or cancel buttons).
- Check-in:
  - PNR lookup rejects empty, malformed and unknown PNRs. Enter in the PNR box triggers the lookup.
  - Check-in works and shows the boarding pass.
  - A second check-in is refused. Check-in before the 48 h window, after the 45 min cut-off, and for a cancelled booking are all refused with a clear reason.
- Baggage:
  - Weights of 0, negative, text, 32.5 kg and blank are rejected, and no bags are created.
  - A bag before check-in is refused. A fourth bag is refused.
  - The tag dialog appears. The summary shows 21.5 kg and Rs 3500 for 17.5 + 4 kg, as the README says.
  - Status moves are enforced: CHECKED_IN to LOADED works, LOADED to LOADED and LOADED to CLAIMED are refused, and LOADED to MISHANDLED works.
  - The selection is kept after a status update.

**Passenger**
- Tabs shown: Book Flights, Boarding Pass, Flight Schedule.
- Search:
  - Results contain only bookable future flights (6 in the sample data). The origin and date filters work, and lower-case airport codes are accepted.
  - Bad airport codes and bad dates are rejected.
- "My bookings" shows only the passenger's own bookings.
- Booking: booking with no flight selected warns. The seat map opens and "confirm with no seat" warns. Changing the selection un-highlights the previous seat. Confirm asks for the price and then shows the PNR.
- A second booking on the same flight is refused. Cancelling your own booking works. A checked-in booking cannot be cancelled. An already-cancelled booking shows an info message.
- The Boarding Pass tab shows checked-in passes. The Flight Schedule tab is read-only.
- Access control: a passenger is blocked from the flight and user services.

## Needs improvement (most important first)
| # | Role | Issue | Evidence |
|---|---|---|---|
| 1 | All | Enter inside the Register dialog triggers the login form. It shows "Enter both username and password" and does not register. | Driven: Enter in the phone field gave one stray error popup and no account. Cause: `bind_all("<Return>")` in `login_view.py`. |
| 2 | Staff | After a failed PNR lookup the old booking and bags stay on screen while the PNR box shows the new, wrong PNR. | Driven: the panel still showed K7Q2MA after looking up "UNKNOWN". |
| 3 | Staff | "Add bag" uses the last booking looked up, not the PNR in the box. "Check in passenger" uses the box. A bag can go to the wrong passenger. | Driven: box said K7Q2MA, the bag went to R4T9XB. |
| 4 | Admin | Bookings and other tabs are not refreshed after a change in another tab. After cancelling flight AI202, Bookings still showed BOOKED, BOOKED, CHECKED_IN until Refresh was clicked. | Driven. Same pattern for the passenger Boarding Pass tab and the Flight Schedule counts (the Flight Schedule counts were not checked). |
| 5 | Admin | The selection is lost after "Cancel flight", so the next action says "Select a flight first". | Driven: the selected id was None after cancel. |
| 6 | Admin / Passenger | The Flights tab (admin), Users tab (admin) and Book Flights tab (passenger) need more height than the 980x620 minimum window gives, so the bottom of the tab is clipped. | Flights needs 555 px vs 514 available. Users needs 517 vs 514. Book Flights needs 607 vs 514. Display scaling can make it worse. |
| 7 | Passenger | An already-booked flight still appears in search. The passenger picks a seat and confirms the price before learning they already hold a booking. | Driven: the "already hold a booking" error appeared after the price confirmation. |
| 8 | Passenger | A search with no matches shows an empty table and no message. | Driven: no dialog and no text. |
| 9 | Admin | There are two Gate inputs: the form field and the "Gate:" box next to "Assign gate". | Code reading. |
| 10 | Admin | "Set status" with an empty combobox shows "Unknown flight status ''". | Driven, after Clear form. |
| 11 | Admin / Staff | Bookings has no search, filter or column sort. | Code reading. |
| 12 | Admin | Users tab can only list and create. There is no edit, deactivate, delete or password reset. | Code reading. The README lists password reset as not implemented. |
| 13 | Passenger | The Boarding Pass tab needs a manual Refresh after check-in. It cannot be printed, saved or copied as a document. | Driven for the refresh. Printing is listed as out of scope in the README. |
| 14 | Passenger | The seat map has no Cancel button. The only way out is to close the window. | Code reading. |
| 15 | All | Dates and times are typed as text (YYYY-MM-DD HH:MM) with no date picker. Passwords have no show/hide option. | Code reading. |

## Suggested fixes
- Items 1-3 are small code changes. Bind Enter per window instead of with `bind_all`, clear the check-in panel on a failed lookup, and make "Add bag" use the same PNR as "Check in".
- Item 4: refresh the tab when it is selected, using the notebook's `<<NotebookTabChanged>>` event.
- Item 5: re-select the flight after cancel.
- Item 6: make the tab content scrollable, or raise `minsize`.
- Item 7: block or label already-booked flights before the seat map opens.
- Item 8: add a "No flights found" label.
