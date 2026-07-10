# The Sky Behind the Panchang

*A plain-language guide to Tithi, Rashi, Nakshatra — and the simple geometry
that connects them all.*

---

## One circle in the sky

Seen from Earth, the Sun appears to travel a fixed circular path through the
stars over the course of a year. The Moon and planets travel along nearly the
same road. This single circle — the **ecliptic** — is the stage on which the
entire Hindu calendar plays out.

Every position on this circle can be described by one number: a degree from
0° to 360°, like a mile marker on a circular highway. The Sun crawls along it
at about 1° per day, taking a full year to go around. The Moon races at about
13° per day, lapping the circle in under a month. Almost everything in the
Panchang comes from just these two moving points and the angle between them.

## Rashi — the Sun's grid

A circle has no natural divisions, so ancient astronomers drew twelve equal
arcs of 30° each and named every arc after the constellation of stars behind
it: Mesha (the ram), Vrishabha (the bull), Mithuna (the twins), and so on.
These are the **rashis**.

A rashi is not a physical object — it is an *address*. "The Sun is in Mithuna"
simply means the Sun's mile marker currently falls between 60° and 90°. Since
the Sun crosses one rashi per month, the twelve rashis divide the year the way
the twelve months do — and indeed, each Hindu lunar month corresponds to the
Sun's passage through one rashi.

Why twelve? Because the sky itself suggests it: the Moon completes about
twelve of its cycles while the Sun goes around once. Twelve is where the solar
rhythm and the lunar rhythm meet.

## Nakshatra — the Moon's grid

The same circle carries a second, finer grid tuned to the Moon's speed:
**27 nakshatras** of 13°20′ each. The Moon circles the sky in about 27.3 days,
so it spends roughly one night in each nakshatra — which is why they are
called lunar *mansions*, the Moon's lodging for the night.

Unlike rashis, each nakshatra is anchored to an actual identifying star:
Rohini is Aldebaran, Krittika is the Pleiades, Chitra is Spica. Your **janma
nakshatra** — the birth star — is simply the mansion the Moon occupied at the
moment you were born. Each nakshatra further divides into four *padas* of
3°20′ for finer work.

So the sky carries two grids at once: a coarse 12-part grid matching the slow
Sun, and a fine 27-part grid matching the fast Moon. Every point on the circle
has both a rashi address and a nakshatra address.

## Tithi — the angle between them

A tithi is different from both: it is not a place on the circle but a
**relationship** — the angle from the Sun to the Moon.

At new moon (Amavasya) the two sit in the same direction: the angle is 0°.
Because the Moon moves about 12° per day faster than the Sun, the gap grows by
roughly 12° daily. The ancients divided the full 360° cycle into thirty
slices of 12° each — and each slice is one **tithi**, a lunar day. The first
fifteen (the brightening fortnight) are *Shukla Paksha*; the waning fifteen
are *Krishna Paksha*. At 180° the Moon stands opposite the Sun, fully lit:
Purnima.

The Moon's shape and the tithi are the same fact viewed two ways — the angle
determines exactly how much of the Moon's lit half faces Earth. Because the
tithi is defined by an angle rather than by clock hours, it absorbs the
varying speeds of the elliptical orbits automatically; real tithis range from
about 19 to 26 hours long.

## Panchang — the five limbs

*Panchanga* means "five limbs" — five readings taken from the same sky at the
same moment:

1. **Tithi** — the Sun–Moon angle, in 12° slices (30 lunar days)
2. **Vara** — the weekday, running sunrise to sunrise
3. **Nakshatra** — the Moon's mansion among the 27
4. **Yoga** — the *sum* of the Sun's and Moon's positions, in 27 divisions
5. **Karana** — half a tithi (6° of the angle)

Four of the five limbs are pure Sun–Moon geometry; only the vara is a simple
count of days. A traditional panchang is, at heart, a daily bulletin of two
moving points on one circle.

## The lunar birthday: Tithi Pravesha

A birthday on the Hindu calendar is not a date — it is a *configuration*.
Your birth recorded a specific Sun–Moon angle (your tithi) occurring while
the Sun stood in a specific rashi (your lunar month). The angle repeats every
29.5 days, which is why your birth tithi appears in every month of the
panchang. But only once a year does it recur **while the Sun is also back at
its birth position** — and that single annual moment is the **Tithi
Pravesha**, the true lunar birthday. It usually lands within a few days of
the Gregorian birthday, drifting because twelve lunar months (~354 days) run
about eleven days short of a solar year.

## One sky, many readings

Everything above is one picture: a circle, two travelers, two grids, and one
angle. The rashi names the Sun's neighborhood, the nakshatra names the
Moon's, the tithi measures the gap between them, and the panchang publishes
all of it each day. What looks like an intricate system of terms is really a
very old, very elegant piece of observational astronomy — geometry that
priests and farmers could read straight off the sky, and that a few lines of
modern ephemeris code can reproduce to the second.

---

*This guide accompanies a small open-source web app that computes your
Panchang and Tithi Pravesha from birth details and draws the sky that
produced them. The calculations use the Swiss Ephemeris via PyJHora with the
Lahiri ayanamsa.*
