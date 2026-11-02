# Service Directory

A good referral needs up-to-date knowledge: who helps with what, where, in which language, and whether they are open now. This offline directory keeps that in one place, and it also shows coordinators what is missing.

```
python -m service_directory
```

Then open http://127.0.0.1:8039. It needs Python 3.10 or newer.

## What it does

- **Ranked search** by need, using distance, language, opening hours, cost and who a service is for
- **Every result says why,** for example "1.2 km away, speaks the language, open now"
- **Hard filters:** a women-only service is not offered for someone else, and a paid one can be excluded
- **Opening hours** as plain text, such as `Sun-Thu 09:00-17:00; Sat 10:00-13:00`, including periods past midnight
- **Gaps for coordination meetings:** needs with no service in an area, needs with only one provider, and listings not checked in 90 days

Outdated referrals send people on wasted journeys, so each entry records when it was last checked.

## Privacy by design

This holds organisations, not people. Do not enter anything about the person being helped, and the app has no place for it. Contact details should be public service numbers, never a private phone.

## How it is tested

Distances are checked against known values, including across the date line. Opening hours are tested at closing minutes, week wraps and past midnight. Ranking is tested for each factor, and the coordination reports for gaps and stale entries.

## Limits

The ranking weights are judgement calls, so staff should use the list as a starting point. Distance is a straight line and not a travel route. There is no map, and one computer holds the data, so a shared directory needs someone to keep copies up to date.

## Tests

```
python -m unittest discover -s tests
```

MIT licence.
