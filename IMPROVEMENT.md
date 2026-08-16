# Improvements

A record of every bug and security issue found in this codebase, what it did,
and how it was fixed. Each entry names the commit that carries the fix.

Before this branch the application did not run: every authenticated request
raised `OperationalError`. Once that was fixed, the payment flow was still
exploitable for free handouts and any student could make themselves an admin.

**Summary:** 4 blockers, 7 security issues, 9 correctness bugs, 8 improvements
— 18 commits, 56 tests where there were none.

**Verification**

```
python manage.py check          # 0 issues
python manage.py check --deploy # 0 issues (with a real SECRET_KEY)
python manage.py test           # 56 tests, OK
python manage.py makemigrations --check --dry-run  # no changes detected
```

---

## Blockers — the application did not run

### 1. Four missing migrations

`fix: add missing migrations for Department, School and department FKs` — 796ae27

`Department`, `School`, `User.department` and `Handout.department` existed in
`models.py` but no migration had ever been generated for them. The database had
no `accounts_user.department_id` column, so any query that selected a user
failed:

```
>>> User.objects.all()[:2]
OperationalError: no such column: accounts_user.department_id
```

JWT authentication loads the user on every request, so *every* authenticated
endpoint returned a 500. `manage.py check` passes in this state, which is why it
went unnoticed — only `makemigrations --check` reveals it.

**Fix.** Generated the four migrations. Two design decisions came with them:

- Both `department` foreign keys are `null=True`. A superuser created with
  `createsuperuser` has no department, and a non-null column would make the
  command impossible to run. The API still requires a department at
  registration, which is where the requirement actually belongs.
- Both use `on_delete=PROTECT` instead of `CASCADE`. Deleting one department
  would otherwise cascade away every user and handout attached to it.

`Handout.department` defaults to the owning rep's department in `save()`, so
existing create paths do not have to supply it.

### 2. Deploys never ran migrations

`fix: run migrations on deploy and serve static files` — 71e2dd0

`start.sh` ran `migrate` — but nothing ran `start.sh`. The `Dockerfile`'s `CMD`
invoked gunicorn directly, so no deploy ever applied a migration. `start.sh`
also bound port 8080 while `fly.toml` declared `internal_port = 8000`, so it
would not have served traffic even if it had been reached.

**Fix.** `CMD` runs `start.sh`, which migrates and then `exec`s gunicorn on the
port Fly expects. `exec` matters: it makes gunicorn PID 1 so it receives
`SIGTERM` directly and shuts workers down gracefully. A Fly `release_command`
also applies migrations once per release rather than in every starting machine.
The image moved from Python 3.10 to 3.12, dropped a duplicate gunicorn install,
and now runs as a non-root user.

### 3. `MOMO_SUBSCRIPTION_KEY` was never defined

`fix: repair the MoMo client and stop truncating amounts` — 5287381

`payments/momo.py` read `settings.MOMO_SUBSCRIPTION_KEY`, which appeared nowhere
in `settings.py`. Every call raised `AttributeError` inside
`initiate_momo_payment`, where a blanket `except Exception` turned it into a
generic 502. Payments were 100% broken, and the error message pointed at MTN
rather than at the missing setting.

`verify_payment` had the mirror-image bug: it omitted the subscription key from
its headers, so verification would have been rejected even once initiation
worked.

**Fix.** Declared the setting, sent the key on both calls, and added an explicit
configuration check that reports exactly which credentials are missing instead
of failing deep inside a request.

### 4. `clerk_auth` referenced fields that do not exist

`fix: remove the unauthenticated token-minting endpoint` — bf60456

The endpoint queried `User.email` and set `User.username`. `email` was dropped
in `accounts/0002` and `username` never existed, so every call raised
`FieldError`. See §5 — it was removed rather than repaired.

---

## Security

### 5. Authentication bypass: `POST /api/accounts/clerk-auth/`

`fix: remove the unauthenticated token-minting endpoint` — bf60456

```python
@api_view(['POST'])
@permission_classes([AllowAny])
def clerk_auth(request):
    email = request.data.get('email')
    user, created = User.objects.get_or_create(email=email, ...)
    refresh = RefreshToken.for_user(user)
    return Response({'access': str(refresh.access_token), ...})
```

An unauthenticated caller supplies an email string and receives a valid JWT for
that user. No Clerk session token is verified — nothing is verified. Anyone who
knew or guessed an account's email could log in as them. `get_or_create` means
an unknown email silently creates a new account instead of failing.

**Fix.** Removed. Repairing the field names would have shipped a working
authentication bypass, which is strictly worse than the broken version. If Clerk
is reintroduced, the endpoint must verify Clerk's signed session JWT against
their JWKS endpoint before issuing any token of ours, and must look the user up
by a stored Clerk subject ID rather than by an attacker-supplied email.

### 6. Privilege escalation: `PATCH /api/accounts/me/`

`fix: block role escalation through the profile endpoint` — 51f3cb5

`MeView` is a `RetrieveUpdateAPIView` and `UserSerializer` declared no
`read_only_fields`, so every field including `role` was writable:

```
PATCH /api/accounts/me/   {"role": "admin"}
```

Any student could promote themselves to admin, which defeats every
`IsRepOrAdmin` check in the project. `student_id` — the login identifier — was
equally writable, so an account could also be renamed onto another student's ID.

**Fix.** `id`, `student_id`, `role` and `created_at` are read-only on
`UserSerializer`. `role` is read-only on `RegisterSerializer` too: it previously
relied on a `validate_role` deny-list, and a field that cannot be written is a
stronger guarantee than a validator that has to remember what to reject. Tests
assert both the escalation attempt and the `student_id` change fail.

### 7. Free handouts: the MoMo callback was forgeable

`fix: verify MoMo callbacks with MTN before confirming payments` — 95fe91a

`MoMoCallbackView` is `AllowAny` with no signature check, and it believed the
`status` field in the request body. `POST /initiate/` returns the caller their
own `reference`. So a student could pay for nothing:

```
POST /api/payments/initiate/     → {"reference": "b3f1…"}   # cancel the prompt
POST /api/payments/callback/     {"correlatorId": "b3f1…", "status": "SUCCESSFUL"}
```

The payment was marked successful, stock decremented, handout released, no money
moved. References are UUIDs, but the attacker does not need to guess one — the
API hands them their own.

**Fix.** The callback body is now treated purely as a hint that *something*
changed. The endpoint looks up the payment and re-queries MTN for the
authoritative status before any state transition; the body's `status` is never
read. Additionally:

- An optional `MOMO_CALLBACK_TOKEN` shared secret is compared in constant time
  when configured, as defence in depth.
- Unknown references are acknowledged with 200 so the endpoint does not confirm
  which references exist.
- If MTN cannot be reached the response is 503, so MTN retries rather than the
  notification being silently dropped.

Regression test: `test_forged_success_callback_does_not_confirm_a_payment`.

### 8. Any rep could edit any other rep's courses and handouts

`feat: enforce object-level ownership on courses and handouts` — 5f093e4

`IsRepOrAdmin` implemented only `has_permission`, which answers "is this user a
rep?" and never "does this user own *this* object?". `CourseDetailView` and
`HandoutDetailView` therefore let any authenticated rep `PUT` or `DELETE`
another rep's records by id — including repricing a competitor's handout to
0.01 or deleting it outright.

**Fix.** `IsOwningRepOrAdmin` adds `has_object_permission`, resolving the owner
through a dotted `owner_field` (`rep` for courses, `course.rep` for handouts).
Handout creation also rejects a `course_id` the caller does not own, which was
an unchecked path to attaching handouts to someone else's course.

### 9. Every student saw every department's catalogue

`fix: scope courses and handouts to the caller's department` — 29804c4

`get_queryset` filtered by rep for reps and returned everything to everyone
else. The detail views had no scoping at all, so any authenticated user could
read any handout by guessing its id.

The old code also did this:

```python
department = Department.objects.get(user=user)
```

— a join to fetch the department already available as `user.department_id` on
the request, executed on every list request including those of students, where
the result was then unused.

**Fix.** Scoping lives in a mixin shared by both the list and detail views, so
they cannot drift apart. Students see only their own department and **fail
closed**: a student with no department sees nothing rather than everything.

### 10. Hard-coded `SECRET_KEY`, `DEBUG = True` in production

`feat: load secrets and deployment config from the environment` — 2414d91

The signing key was a literal in a tracked file, and `DEBUG` was pinned to
`True` on a deployed app — exposing full tracebacks, settings and the SQL of
every failed request to anyone who could trigger an error. A known `SECRET_KEY`
also means session cookies and password-reset tokens can be forged.

**Fix.** Both come from the environment. Startup raises `ImproperlyConfigured`
when `DEBUG` is False and no `SECRET_KEY` is set, so the app cannot silently
ship insecure. Outside DEBUG it now sets HSTS, secure session and CSRF cookies,
SSL redirect, `nosniff` and `X-Frame-Options: DENY`. `manage.py check --deploy`
is clean. `ALLOWED_HOSTS` is configurable and includes `.fly.dev`, which was
missing entirely — only `DEBUG=True` was hiding the resulting 400s.

**The existing `SECRET_KEY` is in git history and must be rotated.**

### 11. Credentials written to the logs

`fix: repair the MoMo client…` — 5287381 · `feat: load secrets…` — 2414d91

`momo.py` printed the full OAuth response body and headers on every call:

```python
print("MTN TOKEN BODY:", resp.text)   # contains the bearer token
```

Those lines land in Fly/Render log storage and anywhere logs are shipped. The
callback handler printed entire request bodies, `settings.py` printed proxy
environment variables at import, and Hubtel's client secret travelled in a query
string that was logged on failure.

**Fix.** All `print()` calls removed — the codebase now has none. Structured
logging via a `LOGGING` config records status codes and correlator IDs, never
response bodies or credentials.

---

## Correctness bugs

### 12. Payments were confirmed non-atomically, and stock was oversold

`fix: confirm payments atomically and stop overselling stock` — 420e978

Nothing in the payment path took a lock — the codebase contained no
`transaction.atomic` and no `select_for_update` anywhere. Three distinct
failures:

**Double decrement.** `PaymentStatusView` and `MoMoCallbackView` each carried
their own copy of the "mark successful, decrement stock" logic. Two concurrent
requests — a poll and a callback arriving together, which is the normal case —
could both observe a pending payment and both decrement, selling one copy twice.

**Lost updates.** `handout.stock -= 1; handout.save()` is a read-modify-write.
Two simultaneous confirmations both read 5, both write 4.

**Oversell at initiation.** `validate()` checked `handout.has_stock()` with
nothing serialising the check. Ten students could all pass it against a single
remaining copy and all be charged.

**Fix.** Confirmation moved into `payments/services.py` as one idempotent
operation used by every caller, taking `select_for_update` on the payment and
returning early if it is already successful. Stock is decremented with a
conditional update:

```python
Handout.objects.filter(pk=..., stock__gt=0).update(stock=F("stock") - 1)
```

`F()` removes the read-modify-write; `stock__gt=0` means the counter cannot be
driven negative by a race; the affected-row count tells us if we oversold, which
is logged as an error rather than passing silently.

Initiation now locks the handout row and re-checks availability inside the
transaction, counting *pending* payments against stock — pending attempts hold a
reservation, so ten simultaneous buyers of one copy produce one payment and nine
rejections.

### 13. Payment history was deleted from inside `validate()`

`fix: confirm payments atomically…` — 420e978

```python
elif existing.status in ["failed", "expired"]:
    existing.delete()
```

A destructive side effect inside a validation method — a place DRF may call more
than once, and which callers reasonably assume is read-only. It existed only to
work around `unique_together = ("student", "handout")`, which otherwise made a
single failed attempt permanently block that student from ever retrying.

**Fix.** Replaced the constraint with a conditional one:

```python
UniqueConstraint(fields=["student", "handout"],
                 condition=Q(status="successful"))
```

A student may retry as often as they like but can only ever hold one *successful*
payment per handout. `validate()` no longer deletes anything, and the audit
trail survives.

### 14. Amounts were truncated — students undercharged

`fix: repair the MoMo client and stop truncating amounts` — 5287381

```python
"amount": str(int(float(payment.amount)))
```

`Decimal("10.50")` → `10.50` → `10`. A GHS 10.50 handout charged GHS 10. The
pesewas were dropped on every payment with a non-zero fractional part, and the
local `Payment.amount` recorded a figure that was never charged.

**Fix.** `format(payment.amount, "f")` formats the `Decimal` directly, preserving
exact value and scale — no float round-trip.

### 15. `has_stock()` crashed on a null stock

`fix: add missing migrations…` — 796ae27

`stock` was declared `null=True` while `has_stock()` did `self.stock > 0`, which
raises `TypeError` on `None`. The serializer exposed `in_stock` through that
method, so one null-stock row would 500 the entire handout list.

**Fix.** `stock` is non-null (it is a `PositiveIntegerField` with `default=0`;
`null=True` served no purpose). `has_stock()` still coerces defensively for
legacy rows.

### 16. `expire_pending_payments` wrote off successful payments

`fix: reconcile pending payments with MTN before expiring them` — cd6e197

The task flipped every pending payment older than 30 minutes to `expired`
without ever asking MTN what had happened. A payment the student *had* approved,
just slowly, was written off — money gone from their wallet, handout never
released, and the record marked expired so nothing would ever reconcile it.

**Fix.** The task now queries MTN for each stale payment and confirms or fails
it on the real status. Expiry is reserved for payments MTN still cannot resolve
after 24 hours. The batch is bounded at 200 so one run cannot stall the worker.

### 17. The notifications app was broken in four ways, and dead

`fix: repair receipts and send them when a payment is confirmed` — 0259245

`send_receipt` was never called from anywhere. Had it been, it would have failed
four times over:

| Defect | Result |
| --- | --- |
| `send_email(to=...)` vs `def send_email(to_email, ...)` | `TypeError` |
| `student.email` — field removed in `accounts/0002` | `AttributeError` |
| `HUBTEL_CLIENT_ID` / `_SECRET` / `_SENDER_ID`, `DEFAULT_FROM_EMAIL` undefined | `AttributeError` on first SMS |
| `payment.confirmed_at.strftime(...)` before `confirmed_at` is guaranteed set | `AttributeError` on `None` |

Every `Notification` row was also written with `sent=True` regardless of whether
the gateway had accepted it, making the delivery log worthless.

**Fix.** All four repaired, the settings declared, and the task wired to fire
from `confirm_payment` via `transaction.on_commit` — so a receipt is only queued
once the payment is durably committed, and a broker outage cannot fail the
payment. The email branch is dropped since the model has no email field.
Delivery outcome is now recorded honestly, transient failures retry, and the
Hubtel call has a timeout so a hung connection cannot pin a worker forever.

### 18. Superusers could not use the API they administer

`fix: give superusers the admin role` — 988f720

`create_superuser` never set `role`, so it defaulted to `"student"`. Every
`IsRepOrAdmin` check compares against `user.role`, so a freshly created
superuser was refused by the entire write API.

**Fix.** `create_superuser` sets `role="admin"`, and asserts the staff and
superuser flags rather than silently accepting `is_staff=False`.

### 19. `stock` was decremented in a `GET` handler

`fix: confirm payments atomically…` — 420e978

`PaymentStatusView.get_object()` called MTN, wrote payment status and mutated
stock — all from a retrieval handler, making `GET` non-idempotent.

**Fix, with a caveat.** Reconciliation is now idempotent and transactional, so
repeated polls are safe. It was *kept* on the `GET` rather than moved to a `POST`
because the frontend polls this endpoint and callbacks are not guaranteed to
arrive — removing it would strand payments as pending whenever MTN's callback
fails. This is a deliberate compromise: the correctness problem (the race) is
fixed, the REST-purity problem is not. If the frontend is updated, this belongs
behind an explicit `POST /payments/<ref>/verify/`.

### 20. Unordered pagination

`test: cover the auth, ownership and payment fixes` — 340d311

`Course` had no `Meta.ordering`, and DRF paginates it. Without a deterministic
order the database may return rows in a different sequence per query, so a row
can appear on two pages or on none. Surfaced by DRF's
`UnorderedObjectListWarning` once tests existed to trigger it. `Payment` and
`Handout` got explicit orderings for the same reason.

---

## Improvements

### 21. A database full of password hashes was committed

`chore: untrack sqlite database and .DS_Store` — 9e30999

`db.sqlite3` was tracked in git, containing real user rows and their password
hashes, alongside `.DS_Store`. `.gitignore` covered neither.

**Fix.** Both untracked, `.gitignore` and `.dockerignore` extended.

> **This does not remove them from history.** The file is still reachable in
> earlier commits. Purge it with `git filter-repo --path db.sqlite3 --invert-paths`
> (or BFG), force-push, and treat every credential in that database as
> compromised.

Related: the app also ran on SQLite in production. A Fly machine's filesystem is
ephemeral and `auto_stop_machines = true` is set, so **the database was being
wiped on every restart**. `dj_database_url` and `psycopg2-binary` were already
dependencies but unused; `DATABASE_URL` is now honoured, making Postgres a
config change rather than a code change.

### 22. No rate limiting anywhere

`feat: rate limit login, registration and payment endpoints` — bea698c

`/login/` was an unmetered oracle for brute-forcing passwords against known
student IDs — and student IDs are sequential and public. `/register/rep/` could
be hammered to guess the invite code. `/initiate/` could be driven in a loop to
spam MoMo prompts at arbitrary phone numbers.

**Fix.** `ScopedRateThrottle` with per-endpoint budgets, all configurable
through `THROTTLE_*` environment variables.

### 23. Long-lived, non-revocable tokens

`feat: rotate refresh tokens and add logout` — 51d6eda

Access tokens lasted a day, refresh tokens a week, and neither could be revoked.
A leaked token was valid for its full lifetime and logging out did nothing
server-side.

**Fix.** Access tokens default to 60 minutes, refresh tokens rotate on use with
the previous one blacklisted, and `POST /api/accounts/logout/` revokes a refresh
token explicitly.

### 24. Registration was impossible to complete

`feat: expose departments and register the admin models` — 90d178b

Registration requires a department, but no department could be created (every
`admin.py` was an empty stub) and none could be listed (the `department` app had
no views). Signup was unusable end to end.

**Fix.** `GET /api/departments/` lists active departments for the signup form —
public, since it is needed before the user has an account. All seven models are
registered in the admin; `User` uses Django's `UserAdmin` so passwords are
hashed rather than stored as typed. `Payment` is read-only in the admin, because
editing a status by hand would desynchronise stock.

### 25. Static files were never served

`fix: run migrations on deploy and serve static files` — 71e2dd0

`collectstatic` ran, but gunicorn does not serve `/static/` and no WhiteNoise was
installed. The admin was unstyled in production; `DEBUG=True` was masking it.

**Fix.** WhiteNoise added to middleware with compressed manifest storage.

### 26. Rep invite code was comparable in variable time, and failed open

`fix: block role escalation through the profile endpoint` — 51f3cb5

`if value != settings.REP_INVITE_CODE` is a short-circuiting comparison, and
`REP_INVITE_CODE` had no default — so `settings.py` raised at import when it was
unset, which also meant `docker build` failed at the `collectstatic` step on a
clean checkout.

**Fix.** `constant_time_compare`, and an explicit refusal when no code is
configured — rep registration fails closed rather than crashing the build.

### 27. Smaller cleanups

- `handouts/serializers.py` used `__import__("courses.models", fromlist=["Course"])`
  where a plain import works. — 5f093e4
- `StudentTokenObtainPairView`, a *view*, was defined in `serializers.py`. — 51f3cb5
- Ghana phone validation was duplicated across two serializers and rejected the
  `+233` form. Now shared in `accounts/validators.py` and normalising. — 51f3cb5
- `import os` appeared three times in `settings.py`, which also mutated global
  proxy environment variables at import time. — 2414d91
- `CourseSerializer.get_handout_count` issued one `COUNT` per course (N+1). Now
  a single annotated aggregate. — 29804c4
- Payment list endpoints lacked `select_related`, issuing four queries per row
  for the nested student/handout/course/rep. — 420e978
- `django-celery-beat` was a dependency but absent from `INSTALLED_APPS`. — 2414d91
- `TIME_ZONE` was `UTC` for a Ghana-only product; now `Africa/Accra`. — 2414d91
- Every environment variable is documented in `.env.example`. — 2414d91

---

## Recommended next steps

Out of scope for this branch, but worth doing:

1. **Purge `db.sqlite3` from git history and rotate every secret in it** — the
   old `SECRET_KEY` and all password hashes are still reachable in earlier
   commits.
2. **Provision Postgres and set `DATABASE_URL`.** The code is ready; until this
   is done, production data is still lost on every machine restart.
3. **Confirm MTN's real callback authentication.** `MOMO_CALLBACK_TOKEN` is a
   shared-secret placeholder. If MTN signs callbacks (HMAC or mTLS), verify the
   signature instead. Re-verification already makes forgery useless, so this is
   defence in depth.
4. **Add a `Payment` state-machine test at the database level** — ideally a
   concurrency test against Postgres, since SQLite's locking hides some of the
   races the `select_for_update` calls are there to prevent.
5. **Reconsider `PaymentStatusView`'s GET side effects** once the frontend can
   call an explicit verify endpoint (§19).
