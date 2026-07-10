#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tithi Pravesha — Web Front End
==============================
Streamlit app wrapping tithi_pravesha_engine.py (unmodified).

  • Single-person input via web form (no CSV)
  • Output identical to the console output of the tier-3 script
  • Interactive rashi/nakshatra schematic with a day slider,
    anchored to the person's real birth sky (PyJHora positions)

Run:
    pip install streamlit          # plus the tier-3 requirements
    streamlit run tithi_web_app.py

Keep this file in the SAME folder as tithi_pravesha_engine.py.
"""
import datetime as _dt
from datetime import timezone, timedelta

import pytz
import streamlit as st
import streamlit.components.v1 as components

# ── import your existing engine, unmodified ──────────────────────────────────
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
try:
    import tithi_pravesha_engine as tp
except ModuleNotFoundError:
    st.set_page_config(page_title="Tithi Pravesha", page_icon="🌙")
    st.error(
        f"**Engine not found.**\n\n"
        f"Looked in: `{_HERE}`\n\n"
        f"Python files present there: "
        f"`{[f for f in os.listdir(_HERE) if f.endswith(('.py', '.txt'))]}`\n\n"
        "Place **tithi_pravesha_engine.py** in that folder — exact "
        "name, no spaces, no `(1)` suffix, no `.txt` extension."
    )
    st.stop()
from jhora.panchanga import drik

st.set_page_config(page_title="Tithi Pravesha", page_icon="🌙", layout="centered")

# ── theme to match the schematic ──────────────────────────────────────────────
st.markdown("""
<style>
  .stApp { background:#131A30; color:#EDEAE0; }
  h1,h2,h3 { font-family: Georgia, serif !important; font-weight:400 !important; }
  h1 em { color:#F2B441; font-style:normal; }
  .stButton>button { background:#E0604A; color:#fff; border:none; border-radius:10px;
                     padding:.6rem 1.2rem; font-weight:600; }
  code, pre { font-size:.8rem !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("# Tithi <em>Pravesha</em>", unsafe_allow_html=True)
st.caption("Birth place anchors the tithi moment; current residence anchors the local sunrise day.")

tab_calc, tab_learn = st.tabs(["🌙 Calculator", "📖 Learn"])

with tab_calc:
    COMMON_TZ = ["Asia/Kolkata", "America/New_York", "America/Chicago", "America/Denver",
                 "America/Los_Angeles", "Europe/London", "Europe/Berlin", "Asia/Dubai",
                 "Asia/Singapore", "Australia/Sydney", "UTC"]

    # ── input form (one person) ───────────────────────────────────────────────────
    st.subheader("Birth details")
    name = st.text_input("Name", "", placeholder="Full name")
    c1, c2 = st.columns(2)
    with c1:
        bdate = st.date_input("Birth date", _dt.date(1990, 1, 1),
                              min_value=_dt.date(1900, 1, 1),
                              max_value=_dt.date.today())
    with c2:
        btime = st.time_input("Birth time (local)", _dt.time(12, 0), step=60)
    c3, c4 = st.columns(2)
    with c3:
        btz = st.selectbox("Birth timezone", COMMON_TZ, index=0)
    with c4:
        bplace = st.text_input("Birth place (city)", "", placeholder="e.g. Chennai")
    with st.expander("…or enter birth coordinates directly"):
        c5, c6 = st.columns(2)
        blat = c5.text_input("Birth latitude", "")
        blon = c6.text_input("Birth longitude", "")

    st.subheader("Current residence")
    use_curr = st.checkbox("Different from birth place", value=False)
    cplace = ctz = ""
    clat = clon = ""
    if use_curr:
        c7, c8 = st.columns(2)
        with c7:
            cplace = st.text_input("Current place (city)", "", placeholder="e.g. London")
        with c8:
            ctz = st.selectbox("Current timezone", COMMON_TZ, index=0)
        with st.expander("…or enter current coordinates directly"):
            c9, c10 = st.columns(2)
            clat = c9.text_input("Current latitude", "")
            clon = c10.text_input("Current longitude", "")

    year = st.number_input("Target year for Pravesha", 1950, 2100,
                           _dt.date.today().year)
    go = st.button("Cast the sky 🌙", type="primary")

    # ── schematic HTML template (values injected via tokens) ─────────────────────
    SCHEMATIC = r"""
    <div id="wrap" style="max-width:560px;margin:0 auto;font-family:-apple-system,'Segoe UI',Roboto,sans-serif;color:#EDEAE0;">
    <div style="width:100%;aspect-ratio:1.02;background:#0E1426;border:1px solid #3B466B;border-radius:14px;overflow:hidden;">
    <svg id="sky" viewBox="0 0 220 216" style="width:100%;height:100%;display:block;"></svg></div>
    <div style="display:flex;align-items:center;gap:10px;margin:10px 0 4px;">
      <input type="range" id="sl" min="0" max="60" step="0.1" value="0"
             style="flex:1;accent-color:#E0604A;height:28px;">
      <div id="val" style="font-size:.78rem;color:#9AA3C0;width:120px;text-align:right;"></div>
    </div>
    <div style="text-align:center;margin-bottom:6px;">
      <button id="rst" style="background:#1B2440;border:1px solid #F2B441;color:#F2B441;border-radius:10px;
        padding:7px 14px;font-size:.8rem;cursor:pointer;">⟲ Back to birth day — __BDATE__</button>
    </div>
    <div id="stat" style="text-align:center;min-height:1.5em;font-size:.83rem;color:#F2B441;"></div>
    </div>
    <script>
    (function(){
    const SUNS=__SUNS__, MOONS=__MOONS__, STEP=__STEP__, ASC0=__ASC__;
    const SUN0=SUNS[0], MOON0=MOONS[0], GAP0=((MOON0-SUN0)%360+360)%360;
    function wrap180(x){x=((x%360)+360)%360;return x>180?x-360:x;}
    function interp(arr,day){
     let i=Math.floor(day/STEP); i=Math.max(0,Math.min(i,arr.length-2));
     const f=day/STEP-i, a=arr[i], d=wrap180(arr[i+1]-a);
     return ((a+d*f)%360+360)%360;
    }
    const NAK=["Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra","Punarvasu",
    "Pushya","Ashlesha","Magha","P.Phalguni","U.Phalguni","Hasta","Chitra","Swati",
    "Vishakha","Anuradha","Jyeshtha","Mula","P.Ashadha","U.Ashadha","Shravana",
    "Dhanishta","Shatabhisha","P.Bhadrapada","U.Bhadrapada","Revati"];
    // traditional nakshatra symbols (emoji approximations):
    // horse's head, yoni, razor, chariot wheel, deer head, teardrop, bow & quiver,
    // flower/udder, serpent, royal throne, bed legs (front/back), hand, jewel,
    // wind-swayed sprout, triumphal arch, lotus, amulet, root bunch, water (Apas),
    // elephant tusk, ear, drum, empty circle, crossed swords, serpent of the deep, fish
    const NGLYPH=["🐎","🔻","🔪","🛞","🦌","💧","🏹","🌸","🐍","👑","🛏️","🛏️","✋","💎",
    "🌿","⛩️","🪷","🧿","🌱","🌊","🐘","👂","🥁","⭕","⚔️","🐉","🐟"];
    const RASHI=["Mesha","Vrishabha","Mithuna","Karka","Simha","Kanya",
    "Tula","Vrischika","Dhanu","Makara","Kumbha","Meena"];
    const RGLYPH=["♈","♉","♊","♋","♌","♍","♎","♏","♐","♑","♒","♓"];
    const TITHI=["Pratipada","Dwitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami",
    "Ashtami","Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi"];
    const svg=document.getElementById('sky'),NS="http://www.w3.org/2000/svg";
    const CX=110,CY=108;
    function el(t,a,p){const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);(p||svg).appendChild(e);return e;}
    function txt(x,y,s,size,fill,anchor,p){const t=el('text',{x,y,'font-size':size,fill,
     'text-anchor':anchor||'middle','font-family':'Georgia,serif'},p);t.textContent=s;return t;}
    function pt(lon,r){const a=(180-lon)*Math.PI/180;return[CX+r*Math.cos(a),CY-r*Math.sin(a)];}
    function band(L0,W,r1,r2){
     const[a1,b1]=pt(L0,r1),[a2,b2]=pt(L0+W,r1),[a3,b3]=pt(L0+W,r2),[a4,b4]=pt(L0,r2);
     return`M ${a1} ${b1} A ${r1} ${r1} 0 0 0 ${a2} ${b2} L ${a3} ${b3} A ${r2} ${r2} 0 0 1 ${a4} ${b4} Z`;}
    function tithiName(e){const n=Math.floor(e/12)+1;
     if(n===15)return"Purnima";if(n>=30)return"Amavasya";
     return(n<=14?"Shukla ":"Krishna ")+TITHI[(n-1)%15];}
    // static rings
    el('circle',{cx:CX,cy:CY,r:96,fill:'none',stroke:'#3B466B','stroke-width':1});
    for(let i=0;i<12;i++){
     const[x1,y1]=pt(i*30,86),[x2,y2]=pt(i*30,96);
     el('line',{x1,y1,x2,y2,stroke:'#3B466B','stroke-width':.7});
     const[gx,gy]=pt(i*30+15,91);
     txt(gx,gy+2.2,RGLYPH[i],6,'#AEB6D4');
     const[tx,ty]=pt(i*30+15,102);txt(tx,ty+2,RASHI[i],4.4,'#6E7899');}
    el('circle',{cx:CX,cy:CY,r:68,fill:'none',stroke:'#3B466B','stroke-width':.5});
    el('circle',{cx:CX,cy:CY,r:80,fill:'none',stroke:'#3B466B','stroke-width':.5});
    for(let i=0;i<27;i++){
     const[x1,y1]=pt(i*(360/27),68),[x2,y2]=pt(i*(360/27),80);
     el('line',{x1,y1,x2,y2,stroke:'#3B466B','stroke-width':.5});
     const[gx,gy]=pt(i*(360/27)+360/54,74);
     txt(gx,gy+1.8,NGLYPH[i],4.8,'#AEB6D4');}
    // natal anchors
    const[nsx,nsy]=pt(SUN0,96),[nmx,nmy]=pt(MOON0,96);
    el('circle',{cx:nsx,cy:nsy,r:5,fill:'none',stroke:'#F2B441','stroke-width':.9,'stroke-dasharray':'2 2',opacity:.7});
    el('circle',{cx:nmx,cy:nmy,r:5,fill:'none',stroke:'#F2B441','stroke-width':.9,'stroke-dasharray':'2 2',opacity:.7});
    // birth lagna marker (valid at day 0 only)
    const[lx1,ly1]=pt(ASC0,96),[lx2,ly2]=pt(ASC0,106);
    el('line',{x1:lx1,y1:ly1,x2:lx2,y2:ly2,stroke:'#7FC98F','stroke-width':1.5});
    const[llx,lly]=pt(ASC0,112);txt(llx,lly+2,"Lagna (at birth)",4.4,'#7FC98F');
    // dynamic layer
    const nakBand=el('path',{fill:'rgba(216,222,234,.20)',stroke:'#D8DEEA','stroke-width':.6});
    const nakLbl=txt(0,0,"",4.8,'#D8DEEA');
    const wedge=el('path',{fill:'rgba(224,96,74,.14)',stroke:'#E0604A','stroke-width':1.2});
    const degLbl=txt(CX,CY-8,"",7,'#E0604A');
    const tLbl=txt(CX,CY+2,"",4.6,'#EDEAE0');
    const sunRay=el('line',{stroke:'#F2B441','stroke-width':.8,opacity:.55,'stroke-dasharray':'3 2'});
    const moonRay=el('line',{stroke:'#D8DEEA','stroke-width':.8,opacity:.7,'stroke-dasharray':'3 2'});
    const sunB=el('circle',{r:6,fill:'#F2B441'});
    const moonG=el('g',{});
    el('circle',{cx:0,cy:0,r:5,fill:'#39415F'},moonG);
    const moonLit=el('path',{d:'M 0 -5 A 5 5 0 0 1 0 5 Z',fill:'#D8DEEA'},moonG);
    const sl=document.getElementById('sl'),val=document.getElementById('val'),stat=document.getElementById('stat');
    function render(day){
     const sun=interp(SUNS,day);
     const moon=interp(MOONS,day);
     const gap=((moon-sun)%360+360)%360;
     const[srx,sry]=pt(sun,96),[mrx,mry]=pt(moon,96);
     sunRay.setAttribute('x1',CX);sunRay.setAttribute('y1',CY);
     sunRay.setAttribute('x2',srx);sunRay.setAttribute('y2',sry);
     moonRay.setAttribute('x1',CX);moonRay.setAttribute('y1',CY);
     moonRay.setAttribute('x2',mrx);moonRay.setAttribute('y2',mry);
     const[sbx,sby]=pt(sun,52);sunB.setAttribute('cx',sbx);sunB.setAttribute('cy',sby);
     const[mbx,mby]=pt(moon,52);
     moonG.setAttribute('transform',`translate(${mbx},${mby}) rotate(${sun-180})`);
     const W=360/27,ni=Math.floor(moon/W);
     nakBand.setAttribute('d',band(ni*W,W,68,80));
     const[nlx,nly]=pt(ni*W+W/2,60);
     nakLbl.setAttribute('x',nlx);nakLbl.setAttribute('y',nly+1.5);
     nakLbl.textContent=NGLYPH[ni]+" "+NAK[ni];
     const[ax,ay]=pt(sun,26),[bx,by]=pt(moon,26);
     wedge.setAttribute('d',`M ${CX} ${CY} L ${ax} ${ay} A 26 26 0 ${gap>180?1:0} 0 ${bx} ${by} Z`);
     degLbl.textContent=gap.toFixed(1)+"°";
     tLbl.textContent=tithiName(gap);
     val.textContent="day +"+day.toFixed(1)+" · "+gap.toFixed(0)+"°";
     const sid=day>20&&Math.abs(wrap180(moon-MOON0))<3;
     const syn=day>20&&Math.abs(wrap180(gap-GAP0))<2;
     if(day<0.4)stat.textContent="★ Birth sky: "+tithiName(gap)+" · Moon in "+NAK[ni]+" · Sun in "+RASHI[Math.floor(sun/30)];
     else if(sid&&syn)stat.textContent="★ Moon home AND birth tithi — near-coincidence of both months";
     else if(sid)stat.textContent="★ Sidereal return (~27.3 d): Moon back in "+NAK[Math.floor(MOON0/(360/27))]+" — tithi has moved on";
     else if(syn)stat.textContent="★ Synodic return (~29.5 d): birth tithi is back — Moon in a new mansion";
     else stat.textContent="Moon in "+NAK[ni]+" · Sun in "+RASHI[Math.floor(sun/30)]+" · "+tithiName(gap);
    }
    sl.addEventListener('input',()=>render(parseFloat(sl.value)));
    document.getElementById('rst').addEventListener('click',()=>{sl.value=0;render(0);});
    render(0);
    })();
    </script>
    """

    # ── helpers ───────────────────────────────────────────────────────────────────
    _JD_EPOCH = _dt.datetime(2000, 1, 1, 12, tzinfo=timezone.utc)

    def _jd_ut(dt_utc):
        return 2451545.0 + (dt_utc - _JD_EPOCH).total_seconds() / 86400.0

    def _sidereal_sun_moon(jd_ut):
        """Sidereal Sun/Moon longitudes; drik first, swisseph fallback."""
        try:
            return float(drik.solar_longitude(jd_ut)), float(drik.lunar_longitude(jd_ut))
        except Exception:
            import swisseph as swe
            swe.set_sid_mode(swe.SIDM_LAHIRI)
            flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
            return (swe.calc_ut(jd_ut, swe.SUN, flags)[0][0],
                    swe.calc_ut(jd_ut, swe.MOON, flags)[0][0])

    _SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio",
              "Sagittarius","Capricorn","Aquarius","Pisces"]

    def _asc_full_deg(bc):
        """Reconstruct 0-360 sidereal ascendant from tier-2 dict."""
        try:
            idx = _SIGNS.index(bc.get("lagna", ""))
            return idx * 30 + float(bc.get("lagna_lon") or 0.0)
        except ValueError:
            return 0.0

    _TITHI_NAMES = ["Pratipada","Dwitiya","Tritiya","Chaturthi","Panchami","Shashthi",
        "Saptami","Ashtami","Navami","Dashami","Ekadashi","Dwadashi","Trayodashi",
        "Chaturdashi"]
    _NAK_NAMES = ["Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra",
        "Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni",
        "Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha","Mula",
        "Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha",
        "Purva Bhadrapada","Uttara Bhadrapada","Revati"]
    _YOGA_NAMES = ["Vishkambha","Priti","Ayushman","Saubhagya","Shobhana","Atiganda",
        "Sukarma","Dhriti","Shula","Ganda","Vriddhi","Dhruva","Vyaghata","Harshana",
        "Vajra","Siddhi","Vyatipata","Variyana","Parigha","Shiva","Siddha","Sadhya",
        "Shubha","Shukla","Brahma","Indra","Vaidhriti"]
    _KARANA_MOV = ["Bava","Balava","Kaulava","Taitila","Garaja","Vanija","Vishti"]

    def _moment_panchanga(dt_utc):
        """Tithi/Nakshatra/Yoga/Karana at the exact instant, derived from
        sidereal longitudes — immune to PyJHora tuple-format differences."""
        jd = _jd_ut(dt_utc)
        sun, moon = _sidereal_sun_moon(jd)
        elong = (moon - sun) % 360.0
        n = int(elong // 12) + 1
        if n == 15:   tithi = "Shukla Paksha / Purnima"
        elif n >= 30: tithi = "Krishna Paksha / Amavasya"
        elif n <= 14: tithi = f"Shukla Paksha / {_TITHI_NAMES[n-1]}"
        else:         tithi = f"Krishna Paksha / {_TITHI_NAMES[n-16]}"
        tithi += f"  ({(elong % 12)/12*100:.0f}% elapsed)"
        ni = int(moon // (360/27))
        pada = int((moon % (360/27)) // (360/108)) + 1
        nak = f"{_NAK_NAMES[ni]} Pada {pada}"
        yoga = _YOGA_NAMES[int(((sun + moon) % 360) // (360/27))]
        k = int(elong // 6)
        if k == 0:      karana = "Kimstughna"
        elif k >= 57:   karana = ["Shakuni","Chatushpada","Naga"][k-57]
        else:           karana = _KARANA_MOV[(k-1) % 7]
        return {"tithi": tithi, "nakshatra": nak, "yoga": yoga, "karana": karana,
                "nak_name": _NAK_NAMES[ni], "pada": pada}

    # ── main action ───────────────────────────────────────────────────────────────
    if go:
        tp.configure_jhora(tp.DEFAULT_AYANAMSA)
        lines = [f"  {name}  ({bdate.day:02d}/{bdate.month:02d}/{bdate.year})"]
        try:
            b_lat, b_lon, b_src = tp.resolve_coordinates(bplace, blat, blon, "birth")
            lines.append(f"    Birth location   : {b_src}  ->  ({b_lat:.4f}, {b_lon:.4f})")

            if use_curr and (cplace or clat):
                c_lat, c_lon, c_src = tp.resolve_coordinates(cplace, clat, clon, "current")
                curr_tz = ctz or btz
            else:
                c_lat, c_lon, c_src = b_lat, b_lon, f"same as birth ({b_src})"
                curr_tz = btz
            lines.append(f"    Current location : {c_src}  ->  ({c_lat:.4f}, {c_lon:.4f})")
            lines.append(f"    Current timezone : {curr_tz}")

            birth_utc    = tp.local_to_utc(bdate.year, bdate.month, bdate.day,
                                           btime.hour, btime.minute, btz)
            birth_tz_hrs = tp.tz_offset_hours(btz)
            curr_tz_hrs  = tp.tz_offset_hours(curr_tz)

            with st.spinner("Finding the Pravesha moment…"):
                birth_result_dt, panchanga_desc = tp.find_tithi_pravesha_for_person(
                    birth_utc, birth_tz_hrs, b_lat, b_lon, birth_tz_hrs, int(year))
                same_loc = (c_lat == b_lat and c_lon == b_lon)
                if same_loc:
                    curr_result_dt = birth_result_dt
                else:
                    curr_result_dt, _ = tp.find_tithi_pravesha_for_person(
                        birth_utc, birth_tz_hrs, c_lat, c_lon, curr_tz_hrs, int(year))

            if birth_result_dt is None and curr_result_dt is None:
                st.error(f"No Tithi Pravesha found in {int(year)}.")
                st.stop()

            birth_tz_obj = pytz.timezone(btz)
            if birth_result_dt:
                bl = birth_result_dt.astimezone(birth_tz_obj)
                lines.append(f"    Tithi Pravesha (birth location)  : "
                             f"{bl.strftime('%d %b %Y %H:%M')} {btz}")
            if not same_loc and curr_result_dt:
                cl = curr_result_dt.astimezone(pytz.timezone(curr_tz))
                lines.append(f"    Tithi Pravesha (current location): "
                             f"{cl.strftime('%d %b %Y %H:%M')} {curr_tz}")
                if birth_result_dt and bl.date() != cl.date():
                    lines.append("    ⚠️  Date differs by location!")

            primary_dt = curr_result_dt or birth_result_dt
            place_obj  = drik.Place("", b_lat, b_lon, birth_tz_hrs)

            panch = tp.get_pravesha_panchanga(birth_result_dt or primary_dt,
                                              place_obj, birth_tz_hrs, birth_tz_hrs)
            bc    = tp.get_birth_chart_basics(birth_utc, birth_tz_hrs, b_lat, b_lon)
            muh   = tp.get_muhurta(birth_result_dt or primary_dt,
                                   birth_tz_hrs, b_lat, b_lon)

            bp = bplace or "birth place"
            birth_panch = tp.get_pravesha_panchanga(birth_utc, place_obj,
                                                    birth_tz_hrs, birth_tz_hrs)
            bm = _moment_panchanga(birth_utc)
            lines += [
                f"    ── Birth Chart Basics ({bp}) ──────────────",
                f"    Janma Nakshatra  : {bm['nak_name']} Pada {bm['pada']}",
                f"    Janma Rasi       : {bc['janma_rasi']} ({bc['janma_rasi_sanskrit']})",
                f"    Lagna            : {bc['lagna']} ({bc['lagna_sanskrit']})"
                + (f"  {bc['lagna_lon']:.2f}°" if bc['lagna_lon'] else ""),
                f"    Lunar Month      : {bc['lunar_month']}",
                f"    Samvatsara       : {bc['samvatsara']}",
                f"    ── Panchanga at Birth moment ({bp}) ────────",
                f"    Tithi     : {bm['tithi']}",
                f"    Vara      : {birth_panch['vara']}",
                f"    Nakshatra : {bm['nakshatra']}",
                f"    Yoga      : {bm['yoga']}",
                f"    Karana    : {bm['karana']}",
                f"    Sunrise   : {birth_panch['sunrise']}  Sunset: {birth_panch['sunset']}",
                f"    ── Panchanga at Pravesha ({bp}) ────────────",
                f"    Tithi     : {panchanga_desc}",
                f"    Vara      : {panch['vara']}",
                f"    Nakshatra : {panch['nakshatra']} Pada {panch['nakshatra_pada']}"
                f"{tp.format_end_time(panch['nakshatra_end'])}",
                f"    Yoga      : {panch['yoga']}{tp.format_end_time(panch['yoga_end'])}",
                f"    Karana    : {panch['karana']}{tp.format_end_time(panch['karana_end'])}",
                f"    Sunrise   : {panch['sunrise']}  Sunset: {panch['sunset']}",
            ]
            if panch["chandrashtama"] is True:
                lines.append("    ⚠️  Chandrashtama : Yes — Moon in 8th from natal Moon")
            elif panch["chandrashtama"] is False:
                lines.append("    Chandrashtama : No")
            lines += [
                f"    ── Muhurta / Auspiciousness ─────────────────────",
                f"    {muh['overall']}",
                f"    Rahu Kalam       : {muh['rahu_kalam']}" + (" ⚠️" if muh.get("in_rahu") else ""),
                f"    Gulika Kalam     : {muh['gulika_kalam']}" + (" ⚠️" if muh.get("in_gulika") else ""),
                f"    Yamaganda Kalam  : {muh['yamaganda_kalam']}",
                f"    Abhijit Muhurta  : {muh['abhijit_muhurta']}" + (" ✅" if muh.get("in_abhijit") else ""),
                f"    Vijaya Muhurta   : {muh['vijaya_muhurtha']}",
                f"    Brahma Muhurtha  : {muh['brahma_muhurtha']}",
                f"    Godhuli Muhurtha : {muh['godhuli_muhurtha']}",
                f"    Durmuhurtam      : {muh['durmuhurtam']}",
                f"    Varjyam          : {muh['varjyam']}",
                f"    Amrit Kalam      : {muh['amrit_kalam']}",
                f"    Chandrabalam     : {muh['chandrabalam']}",
                f"    Chandrashtama    : Moon in {muh['chandrashtama_rasi']} "
                f"(ends {muh['chandrashtama_ends']})",
            ]

            st.subheader("Result")
            st.code("\n".join(lines), language=None)

            # ── schematic anchored to the real birth sky ─────────────────────────
            st.subheader("The birth sky — drag forward in time")
            import json as _json
            jd0 = _jd_ut(birth_utc)
            _STEP, _NDAYS = 0.25, 60
            _suns, _moons = [], []
            for _i in range(int(_NDAYS / _STEP) + 1):
                _s, _m = _sidereal_sun_moon(jd0 + _i * _STEP)
                _suns.append(round(_s, 4)); _moons.append(round(_m, 4))
            asc0 = _asc_full_deg(bc)
            html = (SCHEMATIC
                    .replace("__SUNS__",  _json.dumps(_suns))
                    .replace("__MOONS__", _json.dumps(_moons))
                    .replace("__STEP__",  str(_STEP))
                    .replace("__ASC__",   f"{asc0:.4f}")
                    .replace("__BDATE__", bdate.strftime("%d %b %Y")))
            components.html(html, height=640, scrolling=False)
            st.caption("Slider positions are true ephemeris longitudes (sampled every "
                       "6 hours, interpolated) — elliptical-orbit speed variations "
                       "included. Sidereal/synodic return flags trigger on actual "
                       "angular proximity to the natal configuration.")

            # ── optional .ics for this one person ────────────────────────────────
            try:
                from icalendar import Calendar, Event
                cal = Calendar()
                cal.add("prodid", "-//Tithi Pravesha Web//PyJHora//EN")
                cal.add("version", "2.0")
                ev = Event()
                ev.add("summary", f"🌙 {name}'s Tithi Pravesha")
                ev.add("dtstart", primary_dt.astimezone(pytz.timezone(curr_tz)).date())
                ev.add("description", "\n".join(lines))
                cal.add_component(ev)
                st.download_button("⬇ Download .ics calendar event",
                                   data=cal.to_ical(),
                                   file_name=f"tithi_pravesha_{int(year)}.ics",
                                   mime="text/calendar")
            except Exception:
                pass

        except Exception as e:
            st.error(f"Calculation failed: {e}")
            st.exception(e)

# ══════════════════════════════════════════════════════════════════════════════
# LEARN TAB — plain-language explainer with an interactive schematic
# ══════════════════════════════════════════════════════════════════════════════
LEARN_SCHEMATIC = r"""
<div style="max-width:560px;margin:0 auto;font-family:-apple-system,'Segoe UI',Roboto,sans-serif;color:#EDEAE0;">
<div style="width:100%;aspect-ratio:1.02;background:#0E1426;border:1px solid #3B466B;border-radius:14px;overflow:hidden;">
<svg id="lsky" viewBox="0 0 220 216" style="width:100%;height:100%;display:block;"></svg></div>
<div style="display:flex;align-items:center;gap:10px;margin:10px 0 4px;">
  <input type="range" id="lsl" min="0" max="60" step="0.1" value="0"
         style="flex:1;accent-color:#E0604A;height:28px;">
  <div id="lval" style="font-size:.78rem;color:#9AA3C0;width:120px;text-align:right;"></div>
</div>
<div id="lstat" style="text-align:center;min-height:1.5em;font-size:.83rem;color:#F2B441;"></div>
</div>
<script>
(function(){
const SUN_RATE=360/365.2422, MOON_RATE=360/27.32166;
const NAK=["Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra","Punarvasu",
"Pushya","Ashlesha","Magha","P.Phalguni","U.Phalguni","Hasta","Chitra","Swati",
"Vishakha","Anuradha","Jyeshtha","Mula","P.Ashadha","U.Ashadha","Shravana",
"Dhanishta","Shatabhisha","P.Bhadrapada","U.Bhadrapada","Revati"];
const NG=["🐎","🔻","🔪","🛞","🦌","💧","🏹","🌸","🐍","👑","🛏️","🛏️","✋","💎",
"🌿","⛩️","🪷","🧿","🌱","🌊","🐘","👂","🥁","⭕","⚔️","🐉","🐟"];
const RASHI=["Mesha","Vrishabha","Mithuna","Karka","Simha","Kanya",
"Tula","Vrischika","Dhanu","Makara","Kumbha","Meena"];
const RG=["♈","♉","♊","♋","♌","♍","♎","♏","♐","♑","♒","♓"];
const TITHI=["Pratipada","Dwitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami",
"Ashtami","Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi"];
const svg=document.getElementById('lsky'),NS="http://www.w3.org/2000/svg";
const CX=110,CY=108;
function el(t,a,p){const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);(p||svg).appendChild(e);return e;}
function txt(x,y,s,size,fill,anchor,p){const t=el('text',{x,y,'font-size':size,fill,
 'text-anchor':anchor||'middle','font-family':'Georgia,serif'},p);t.textContent=s;return t;}
function pt(lon,r){const a=(180-lon)*Math.PI/180;return[CX+r*Math.cos(a),CY-r*Math.sin(a)];}
function band(L0,W,r1,r2){
 const[a1,b1]=pt(L0,r1),[a2,b2]=pt(L0+W,r1),[a3,b3]=pt(L0+W,r2),[a4,b4]=pt(L0,r2);
 return`M ${a1} ${b1} A ${r1} ${r1} 0 0 0 ${a2} ${b2} L ${a3} ${b3} A ${r2} ${r2} 0 0 1 ${a4} ${b4} Z`;}
function tithiName(e){const n=Math.floor(e/12)+1;
 if(n===15)return"Purnima";if(n>=30)return"Amavasya";
 return(n<=14?"Shukla ":"Krishna ")+TITHI[(n-1)%15];}
function phasePath(R,e){
 e=((e%360)+360)%360;
 const rx=R*Math.abs(Math.cos(e*Math.PI/180));
 if(e===0)return"";
 if(e<=180){const sw=e<90?0:1;
  return`M 0 ${-R} A ${R} ${R} 0 0 1 0 ${R} A ${rx} ${R} 0 0 ${sw} 0 ${-R} Z`;}
 const sw=e>270?1:0;
 return`M 0 ${-R} A ${R} ${R} 0 0 0 0 ${R} A ${rx} ${R} 0 0 ${sw} 0 ${-R} Z`;}
el('circle',{cx:CX,cy:CY,r:96,fill:'none',stroke:'#3B466B','stroke-width':1});
for(let i=0;i<12;i++){
 const[x1,y1]=pt(i*30,86),[x2,y2]=pt(i*30,96);
 el('line',{x1,y1,x2,y2,stroke:'#3B466B','stroke-width':.7});
 const[gx,gy]=pt(i*30+15,91);txt(gx,gy+2.2,RG[i],6,'#AEB6D4');
 const[tx,ty]=pt(i*30+15,102);txt(tx,ty+2,RASHI[i],4.4,'#6E7899');}
el('circle',{cx:CX,cy:CY,r:68,fill:'none',stroke:'#3B466B','stroke-width':.5});
el('circle',{cx:CX,cy:CY,r:80,fill:'none',stroke:'#3B466B','stroke-width':.5});
for(let i=0;i<27;i++){
 const[x1,y1]=pt(i*(360/27),68),[x2,y2]=pt(i*(360/27),80);
 el('line',{x1,y1,x2,y2,stroke:'#3B466B','stroke-width':.5});
 const[gx,gy]=pt(i*(360/27)+360/54,74);txt(gx,gy+1.8,NG[i],4.8,'#AEB6D4');}
const nakBand=el('path',{fill:'rgba(216,222,234,.20)',stroke:'#D8DEEA','stroke-width':.6});
const nakLbl=txt(0,0,"",4.8,'#D8DEEA');
const wedge=el('path',{fill:'rgba(224,96,74,.14)',stroke:'#E0604A','stroke-width':1.2});
const degLbl=txt(CX,CY-8,"",7,'#E0604A');
const tLbl=txt(CX,CY+2,"",4.6,'#EDEAE0');
const sunRay=el('line',{stroke:'#F2B441','stroke-width':.8,opacity:.55,'stroke-dasharray':'3 2'});
const moonRay=el('line',{stroke:'#D8DEEA','stroke-width':.8,opacity:.7,'stroke-dasharray':'3 2'});
const sunB=el('circle',{r:6,fill:'#F2B441'});
const moonG=el('g',{});
el('circle',{cx:0,cy:0,r:5,fill:'#39415F'},moonG);
el('path',{d:'M 0 -5 A 5 5 0 0 1 0 5 Z',fill:'#D8DEEA'},moonG);
el('rect',{x:6,y:6,width:50,height:58,rx:8,fill:'#182036',stroke:'#3B466B','stroke-width':.7});
txt(31,15,"the moon",4.2,'#8B94B5');txt(31,20.5,"that night",4.2,'#8B94B5');
const ig=el('g',{transform:'translate(31,40)'});
el('circle',{cx:0,cy:0,r:12,fill:'#39415F'},ig);
const iLit=el('path',{fill:'#D8DEEA'},ig);
const iPct=txt(31,59,"",4.2,'#EDEAE0');
const sl=document.getElementById('lsl'),val=document.getElementById('lval'),stat=document.getElementById('lstat');
function render(day){
 const sun=(day*SUN_RATE)%360, moon=(day*MOON_RATE)%360;
 const gap=((moon-sun)%360+360)%360;
 const[srx,sry]=pt(sun,96),[mrx,mry]=pt(moon,96);
 sunRay.setAttribute('x1',CX);sunRay.setAttribute('y1',CY);
 sunRay.setAttribute('x2',srx);sunRay.setAttribute('y2',sry);
 moonRay.setAttribute('x1',CX);moonRay.setAttribute('y1',CY);
 moonRay.setAttribute('x2',mrx);moonRay.setAttribute('y2',mry);
 const[sbx,sby]=pt(sun,52);sunB.setAttribute('cx',sbx);sunB.setAttribute('cy',sby);
 const[mbx,mby]=pt(moon,52);
 moonG.setAttribute('transform',`translate(${mbx},${mby}) rotate(${sun-180})`);
 const W=360/27,ni=Math.floor(moon/W);
 nakBand.setAttribute('d',band(ni*W,W,68,80));
 const[nlx,nly]=pt(ni*W+W/2,60);
 nakLbl.setAttribute('x',nlx);nakLbl.setAttribute('y',nly+1.5);
 nakLbl.textContent=NG[ni]+" "+NAK[ni];
 const[ax,ay]=pt(sun,26),[bx,by]=pt(moon,26);
 wedge.setAttribute('d',`M ${CX} ${CY} L ${ax} ${ay} A 26 26 0 ${gap>180?1:0} 0 ${bx} ${by} Z`);
 degLbl.textContent=gap.toFixed(1)+"°";
 tLbl.textContent=tithiName(gap);
 iLit.setAttribute('d',phasePath(12,gap));
 iPct.textContent=Math.round(50*(1-Math.cos(gap*Math.PI/180)))+"% lit";
 val.textContent="day "+day.toFixed(1)+" · "+gap.toFixed(0)+"°";
 if(day<0.4)stat.textContent="★ Amavasya: Sun and Moon in the same direction — angle 0°";
 else if(Math.abs(gap-180)<5)stat.textContent="★ Purnima: Moon opposite the Sun — fully lit";
 else stat.textContent="Moon in "+NAK[ni]+" · Sun in "+RASHI[Math.floor(sun/30)]+" · "+tithiName(gap);
}
sl.addEventListener('input',()=>render(parseFloat(sl.value)));
render(0);
})();
</script>
"""

with tab_learn:
    st.markdown("## The sky behind the Panchang")
    st.markdown(
        "Seen from Earth, the **Sun** traces one fixed circle through the stars "
        "each year — the *ecliptic*. The **Moon** travels nearly the same road, "
        "about 13× faster. Every position on this circle is a mile-marker from "
        "0° to 360°, and almost everything in the Panchang comes from just these "
        "two moving points and the angle between them.")
    st.markdown(
        "**Try it below:** drag the slider to move time forward from a new moon. "
        "Watch the red angle grow ~12° per day, the Moon hop one mansion per "
        "night, and the phase inset track the angle exactly.")
    components.html(LEARN_SCHEMATIC, height=620, scrolling=False)

    st.markdown("### Rashi — the Sun's grid")
    st.markdown(
        "The circle is divided into **12 equal arcs of 30°**, each named for the "
        "constellation behind it (♈ Mesha, ♉ Vrishabha, …). A rashi is an "
        "*address*, not an object: “Sun in Mithuna” means its mile-marker lies "
        "between 60° and 90°. The Sun crosses one rashi per month — which is why "
        "there are twelve months. Twelve is where the solar and lunar rhythms "
        "meet: the Moon completes ~12 cycles while the Sun completes one.")

    st.markdown("### Nakshatra — the Moon's grid")
    st.markdown(
        "The same circle carries a finer grid of **27 mansions of 13°20′**, "
        "matched to the Moon's 27.3-day lap — one lodging per night. Each is "
        "anchored to a real star (Rohini = Aldebaran, Krittika = the Pleiades, "
        "Chitra = Spica). Your *janma nakshatra* is simply the mansion the Moon "
        "occupied at your birth; each divides into 4 *padas* of 3°20′.")

    st.markdown("### Tithi — the angle between them")
    st.markdown(
        "A tithi is not a place but a **relationship**: the angle from Sun to "
        "Moon. At Amavasya the angle is 0°; it grows ~12° per day, and each 12° "
        "slice is one tithi — 30 lunar days per cycle. At 180° the Moon is fully "
        "lit: Purnima. The Moon's shape and the tithi are the same fact: the "
        "angle determines the phase. Because tithi is an angle, the elliptical "
        "orbits' varying speeds are absorbed automatically — real tithis run "
        "~19 to 26 hours.")

    st.markdown("### Panchang — the five limbs")
    st.markdown(
        "*Panchanga* means **five limbs** — five readings of the same sky: "
        "**Tithi** (Sun–Moon angle ÷ 12°), **Vara** (weekday, sunrise to "
        "sunrise), **Nakshatra** (the Moon's mansion), **Yoga** (the *sum* of "
        "Sun and Moon positions in 27 divisions), and **Karana** (half a "
        "tithi). Four of the five are pure Sun–Moon geometry.")

    st.markdown("### Tithi Pravesha — the lunar birthday")
    st.markdown(
        "A Hindu birthday is a *configuration*, not a date: your birth tithi "
        "recurring **while the Sun is back in its birth rashi**. The angle "
        "alone repeats every 29.5 days — but the combination happens once a "
        "year, usually within a few days of the Gregorian birthday (twelve "
        "lunar months run ~11 days short of a solar year). That annual moment "
        "is what the Calculator tab finds.")

    st.markdown("### References & further reading")
    st.markdown(
        "- **PyJHora** — the open-source Vedic astrology library powering this "
        "app: [github.com/naturalstupid/PyJHora](https://github.com/naturalstupid/PyJHora)\n"
        "- **Swiss Ephemeris** — the underlying planetary engine: "
        "[astro.com/swisseph](https://www.astro.com/swisseph/)\n"
        "- **Drik Panchang** — daily panchanga for any location: "
        "[drikpanchang.com](https://www.drikpanchang.com)\n"
        "- Jean Meeus, *Astronomical Algorithms* (Willmann-Bell) — the classic "
        "reference for Sun/Moon position mathematics\n"
        "- P.V.R. Narasimha Rao, *Vedic Astrology: An Integrated Approach* — "
        "includes the Tithi Pravesha technique and its use in annual charts\n"
        "- Pt. Sanjay Rath — tradition and articles on Tithi Pravesha "
        "(srath.com)")
    st.caption(
        "Sidereal positions use the Lahiri (Chitrapaksha) ayanamsa. The "
        "schematic above uses mean motions for teaching; the Calculator tab "
        "uses true ephemeris positions throughout.")