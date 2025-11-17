# Release v1.1: Hub/Spoke Toggle + Plotly Migration
**Date:** November 16, 2025  
**Tag:** `v1.1-hub-spoke-plotly`  
**Branch:** `main` (merged from `feature/hub-spoke-toggle`)

---

## 🎯 **What's New**

### **1. Hub/Spoke Toggle**
Users can now choose their preferred level of detail on the Price Map:
- **Major Hubs (8)** - Fast, proven stable view showing main ERCOT load zones
- **All Nodes (10)** - Includes 2 strategic detail nodes (Houston Central, Midland)

**Location:** Radio button selector above the Price Map  
**Default:** Major Hubs (8) for optimal performance

### **2. Plotly Migration - Working Tooltips!**
Migrated Price Map from pydeck to Plotly Scattermapbox.

**Why?** pydeck HTML tooltips were fundamentally broken - they displayed template literals like `${avg_price:.2f}` instead of actual values.

**Result:** Tooltips now work perfectly, showing:
```
Houston
Price: $79.21/MWh
(7.92 ¢/kWh)
Level: Medium
```

### **3. Visual Consistency**
- White background (`carto-positron` style) matches Generation Map and other tabs
- Same coral/red color scheme maintained (Very Low → Very High)
- Interactive legend at bottom of map
- Better zoom/pan controls

### **4. ETL Enhancement**
Added tier classification to ERCOT LMP data:
- `tier='hub'` - 8 major ERCOT zones (default view)
- `tier='strategic'` - 2 granular nodes for detail

**Discovery:** ERCOT only publishes 10 real settlement points, not 28. Using actual data instead of fake nodes.

---

## 📊 **Technical Changes**

### **Files Modified:**

**1. `etl/ercot_lmp_etl.py`**
- Added `'tier'` column to ERCOT_ZONES dictionary
- Labels: 8 hubs, 2 strategic nodes
- Updated logging to show tier breakdown
- All nodes based on real ERCOT settlement point data

**2. `app/tabs/price_map_tab.py`**
- Replaced `import pydeck as pdk` with `import plotly.graph_objects as go`
- Removed pydeck ScatterplotLayer (broken tooltips)
- Added Plotly Scattermapbox with native hover tooltips
- Added radio button toggle for hub/strategic filtering
- Changed `'zone'` references to `'region'` (actual column name)
- Removed custom HTML legend (Plotly has built-in)
- Applied `carto-positron` map style (white background)

### **Commits:**
```
134418a - ✨ Add hub/spoke toggle to Price Map (8 hubs + 2 strategic nodes)
0271efd - 🐛 Fix tooltip price display - use 'region' column instead of 'zone'
7d7b6e0 - 🗺️ Migrate Price Map to Plotly for reliable tooltips
9f735d2 - 🎨 Set Price Map to white background (matches other tabs)
68dd7d8 - Merge feature/hub-spoke-toggle: Price Map enhancements
```

---

## ✅ **Benefits**

### **For Users:**
- ✅ Tooltips actually work (show real prices)
- ✅ Choose detail level (8 hubs vs 10 nodes)
- ✅ Better interactivity (zoom, pan, click)
- ✅ Visual consistency across tabs

### **For Developers:**
- ✅ Plotly is industry standard (better maintained)
- ✅ Native tooltips (no HTML hacks)
- ✅ Easier to debug and extend
- ✅ Better documentation and community support

### **For Stability:**
- ✅ Graceful degradation still active (from v1.0)
- ✅ Feature branch thoroughly tested
- ✅ Easy rollback to v1.0-working if needed

---

## 🧪 **Testing Completed**

### **Price Map Tab:**
- ✅ Major Hubs (8) mode - Fast rendering, tooltips work
- ✅ All Nodes (10) mode - Shows strategic nodes, tooltips work
- ✅ Toggle switches smoothly between modes
- ✅ Color scaling correct (Very Low=coral, Very High=dark red)
- ✅ Legend displays at bottom of map
- ✅ White background matches other tabs
- ✅ Performance: <2 second load time

### **Other Tabs:**
- ✅ Fuel Mix - Working
- ✅ Generation Map - Working
- ✅ Interconnection Queue - Working
- ✅ Minerals & Critical Minerals - Working
- ✅ About & Data Sources - Working

### **Data Quality:**
- ✅ 10 real ERCOT settlement points
- ✅ Fresh data from November 16, 2025
- ✅ Tier classification correct (8 hubs + 2 strategic)
- ✅ Prices in both formats ($/MWh and ¢/kWh)

---

## 🚨 **Disaster Recovery**

### **If v1.1 Breaks:**

**Option 1: Rollback to v1.0 (stable baseline)**
```bash
git checkout v1.0-working
streamlit run app/main.py --server.port 8501
```

**Option 2: Rollback to v1.1 (this release)**
```bash
git checkout v1.1-hub-spoke-plotly
streamlit run app/main.py --server.port 8501
```

**Option 3: Reset main to v1.0**
```bash
git checkout main
git reset --hard v1.0-working
git push origin main --force
```

### **Recovery Tags Available:**
- `v1.0-working` - November 15, 2025 (pydeck, 8 zones, graceful degradation)
- `v1.1-hub-spoke-plotly` - November 16, 2025 (Plotly, hub/spoke toggle, working tooltips)

---

## 📚 **Known Issues & Future Work**

### **Known Issues:**
- None identified in testing

### **Future Enhancements:**
- Consider migrating Generation Map to Plotly (if tooltips become problematic)
- Consider migrating Queue Map to Plotly (for consistency)
- Add more strategic nodes if ERCOT publishes additional settlement points
- Performance optimization for >20 nodes (if needed in future)

### **Not Planned:**
- ❌ Adding 28 fake nodes (ERCOT only publishes 10 real ones)
- ❌ Reverting to pydeck (tooltips fundamentally broken)

---

## 🎓 **Lessons Learned**

### **What Worked:**
1. ✅ **Feature branch development** - Isolated changes, easy testing
2. ✅ **Incremental commits** - Each change atomic and reversible
3. ✅ **One variable at a time** - Changed only rendering library, kept data same
4. ✅ **Using real data** - 10 ERCOT nodes better than 28 fake nodes
5. ✅ **Industry standards** - Plotly more reliable than custom HTML tooltips

### **What Didn't Work:**
1. ❌ **pydeck HTML tooltips** - Showed template literals, fundamentally broken
2. ❌ **Trying to fix unfixable** - Multiple attempts to fix pydeck tooltips failed
3. ❌ **Too many changes at once** - Previous Nov 12 attempt (Plotly + 28 nodes + data changes) broke everything

### **Key Insight:**
**When a tool is fundamentally broken, switch tools instead of fighting it.**

Spent hours trying to fix pydeck tooltips with:
- Column name changes
- Template string variations
- Conditional logic
- Schema validation

**Solution:** 15 minutes to migrate to Plotly → tooltips worked immediately.

---

## 🔄 **Migration Path from v1.0**

If starting from `v1.0-working`:

```bash
# Pull latest changes
git pull origin main

# Verify you're on v1.1
git log --oneline -1
# Should show: 68dd7d8 Merge feature/hub-spoke-toggle

# Regenerate data with tier classification
cd etl
python ercot_lmp_etl.py

# Restart dashboard
streamlit run app/main.py --server.port 8501
```

---

## 📊 **Performance Metrics**

### **v1.0-working (pydeck, 8 zones):**
- Load time: ~1.5 seconds
- Tooltip status: Broken (template literals)
- Interactivity: Limited (locked viewport)

### **v1.1-hub-spoke-plotly (Plotly, 8-10 zones):**
- Load time: ~1.8 seconds (Major Hubs mode)
- Load time: ~2.0 seconds (All Nodes mode)
- Tooltip status: ✅ Working (actual values)
- Interactivity: Better (zoom, pan, click)

**Verdict:** Slightly slower load (~0.3s) but tooltips actually work. Worth the tradeoff.

---

## 🎯 **Success Criteria Met**

- ✅ Tooltips display actual prices (not template literals)
- ✅ Hub/spoke toggle provides user choice
- ✅ Visual consistency with other tabs (white background)
- ✅ Performance acceptable (<3 seconds)
- ✅ All 6 tabs functional
- ✅ Data fresh (November 16, 2025)
- ✅ Graceful degradation maintained
- ✅ Easy rollback available (tagged releases)

---

**Version:** 1.1  
**Status:** Production Ready ✅  
**Released:** November 16, 2025  
**Maintained By:** Charlie9170  

**Previous Version:** v1.0-working (November 15, 2025)  
**Next Version:** TBD
