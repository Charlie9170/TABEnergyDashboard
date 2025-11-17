# Price Map Node Expansion Research
**Date:** November 16, 2025  
**Branch:** `feature/expand-to-15-nodes`  
**Current:** 10 nodes → **Target:** 15 nodes (maximum available from ERCOT)

---

## 📊 **Research Findings**

### **ERCOT Data Source:**
- URL: https://www.ercot.com/content/cdr/html/real_time_spp
- Updates: Every 5 minutes
- Format: HTML table with settlement point prices

### **Total Settlement Points Available:** 15

ERCOT publishes real-time LMP data for **15 settlement points total**.
We currently use **10** of them.
**We can add 5 more nodes.**

---

## 📍 **Current Nodes (10)**

### **Hubs (8) - tier='hub'**
1. `HB_BUSAVG` - Grid Average
2. `HB_HOUSTON` - Houston
3. `HB_NORTH` - North (Dallas)
4. `HB_PAN` - Panhandle (Amarillo)
5. `HB_SOUTH` - South (Corpus/Laredo)
6. `HB_WEST` - West (Odessa/Midland)
7. `LZ_NORTH` - East (Tyler/Longview)
8. `LZ_SOUTH` - South Central (Austin)

### **Strategic (2) - tier='strategic'**
9. `LZ_HOUSTON` - Houston Central
10. `LZ_WEST` - Midland

---

## 🆕 **Available Nodes to Add (5)**

### **Priority 1: Major Population Centers (4 nodes)**

#### **1. LZ_CPS - CPS Energy Load Zone (San Antonio)**
- **What:** San Antonio metropolitan area
- **Why:** 7th largest US city, 1.5M population
- **Utility:** CPS Energy serves San Antonio
- **Strategic Value:** Major load center, unique pricing vs HB_SOUTH
- **Tier:** `strategic`
- **Coordinates:** ~29.42°N, 98.49°W

#### **2. LZ_LCRA - LCRA Load Zone (Central Texas/Austin area)**
- **What:** Lower Colorado River Authority service area
- **Why:** Austin suburbs, Hill Country, Colorado River basin
- **Utility:** LCRA (municipal power authority)
- **Strategic Value:** Different from LZ_SOUTH hub, covers LCRA territory
- **Tier:** `strategic`
- **Coordinates:** ~30.20°N, 98.00°W

#### **3. LZ_AEN - AEP North Load Zone (Northeast Texas)**
- **What:** American Electric Power North service territory
- **Why:** Northeast Texas (Texarkana area, borders Arkansas/Louisiana)
- **Utility:** AEP Texas (investor-owned utility)
- **Strategic Value:** Border region, different market dynamics
- **Tier:** `strategic`
- **Coordinates:** ~33.25°N, 94.20°W

#### **4. LZ_RAYBN - Rayburn Load Zone (East Texas border)**
- **What:** Named after Sam Rayburn reservoir area
- **Why:** Far east Texas near Louisiana border
- **Utility:** Covers eastern load zone
- **Strategic Value:** Interstate interconnection pricing, unique market
- **Tier:** `strategic`
- **Coordinates:** ~32.00°N, 94.00°W

### **Priority 2: Aggregate Metric (1 node)**

#### **5. HB_HUBAVG - Hub Average**
- **What:** Average of all hub prices (aggregate metric)
- **Why:** Useful for comparing regional prices to hub average
- **Strategic Value:** Reference point for price deviations
- **Tier:** `hub` (it's an aggregate of hubs)
- **Coordinates:** ~31.0°N, 99.5°W (center of Texas, visual reference)

---

## 🎯 **Recommended Expansion Strategy**

### **Phase 1: Add 4 Population Center Nodes (10→14)**

**Nodes to add:**
1. `LZ_CPS` - San Antonio
2. `LZ_LCRA` - Austin area
3. `LZ_AEN` - Northeast Texas
4. `LZ_RAYBN` - East Texas border

**Rationale:**
- Major population centers (San Antonio is huge market)
- Geographic diversity (covers more of Texas)
- Real utility service territories
- Strategic pricing insight

**Expected result:** Good geographic coverage, manageable node count

---

### **Phase 2: Add Hub Average (14→15) - Optional**

**Node to add:**
5. `HB_HUBAVG` - Hub Average

**Rationale:**
- Useful reference metric
- Helps users understand price deviations
- Low risk (aggregate, not geographic point)

**Decision criteria:** Add if 14-node performance is excellent

---

## ✅ **Quality Gates**

After adding 4 nodes (10→14), test:

### **Performance**
- [ ] Map renders in <3 seconds
- [ ] Tooltips appear instantly (<0.5s lag)
- [ ] No browser lag when toggling modes
- [ ] CPU/memory usage acceptable

### **Usability**
- [ ] No node overlap (all markers readable)
- [ ] Colors distinguishable
- [ ] Tooltips clear and not cluttered
- [ ] Legend still readable

### **Functionality**
- [ ] Hub/spoke toggle works (8 vs 14)
- [ ] All tooltips show actual prices
- [ ] All other tabs still functional
- [ ] No console errors

### **Data Quality**
- [ ] ETL fetches prices for all 14 nodes
- [ ] No null/missing data
- [ ] Coordinates accurate (inside Texas)
- [ ] Prices reasonable (not outliers)

---

## 📐 **Proposed Coordinates**

Based on actual utility service territories:

```python
# Add to ERCOT_ZONES in etl/ercot_lmp_etl.py

# Priority 1: Population centers (4 nodes)
'LZ_CPS': {
    'name': 'San Antonio (CPS Energy)', 
    'lat': 29.42, 
    'lon': -98.49, 
    'tier': 'strategic'
},
'LZ_LCRA': {
    'name': 'Austin Area (LCRA)', 
    'lat': 30.20, 
    'lon': -98.00, 
    'tier': 'strategic'
},
'LZ_AEN': {
    'name': 'Northeast Texas (AEP)', 
    'lat': 33.25, 
    'lon': -94.20, 
    'tier': 'strategic'
},
'LZ_RAYBN': {
    'name': 'East Texas (Rayburn)', 
    'lat': 32.00, 
    'lon': -94.00, 
    'tier': 'strategic'
},

# Priority 2: Hub average (1 node - optional)
'HB_HUBAVG': {
    'name': 'Hub Average', 
    'lat': 31.00, 
    'lon': -99.50, 
    'tier': 'hub'
},
```

---

## 🗺️ **Geographic Distribution**

After expansion, coverage will be:

**Current gaps filled:**
- ✅ San Antonio standalone node (was lumped with HB_SOUTH)
- ✅ Austin area detail (was only LZ_SOUTH hub)
- ✅ Northeast Texas (was underrepresented)
- ✅ East Texas border (interstate pricing)

**Still aggregated (acceptable):**
- Odessa/Midland region (HB_WEST + LZ_WEST covers this)
- Houston area (HB_HOUSTON + LZ_HOUSTON covers this)
- El Paso (not in ERCOT, different grid)

---

## 📊 **Expected Performance Impact**

### **Current (10 nodes):**
- Render time: ~1.8 seconds
- Tooltip lag: <0.3 seconds
- File size: 7.2 KB

### **Projected (14 nodes):**
- Render time: ~2.2 seconds (estimate)
- Tooltip lag: <0.4 seconds (estimate)
- File size: ~10 KB (estimate)

### **Projected (15 nodes):**
- Render time: ~2.3 seconds (estimate)
- Tooltip lag: <0.5 seconds (estimate)
- File size: ~11 KB (estimate)

**Verdict:** Should still pass <3 second quality gate

---

## 🚀 **Implementation Plan**

### **Step 1: Add 4 nodes (10→14)**
```bash
# Update etl/ercot_lmp_etl.py
# Add LZ_CPS, LZ_LCRA, LZ_AEN, LZ_RAYBN

# Test ETL
python etl/ercot_lmp_etl.py

# Verify 14 nodes generated
python -c "import pandas as pd; print(len(pd.read_parquet('data/price_map.parquet')))"

# Start dashboard on different port (keep main running)
streamlit run app/main.py --server.port 8502

# Test quality gates
```

### **Step 2: Test quality gates**
- Performance metrics
- Usability check
- Functionality verification
- Data quality validation

### **Step 3: Decision point**
- ✅ If all gates pass → Add HB_HUBAVG (14→15)
- ❌ If any gate fails → Stop at 14, optimize, or revert to 10

### **Step 4: Final testing**
- Test with all 15 nodes (if proceeding)
- Update toggle labels: "Major Hubs (8)" | "All Nodes (15)"
- Comprehensive tab testing

### **Step 5: Merge to main**
- Commit incremental changes
- Tag release: v1.2-15-nodes
- Document performance results

---

## 🎓 **Lessons from Previous Attempts**

### **Nov 12, 2025 - Failed attempt:**
- Tried to add 28 nodes + migrate to Plotly simultaneously
- Too many changes at once
- Dashboard broke completely

### **Nov 16, 2025 - Successful approach:**
- Migrated to Plotly first (one change)
- Tested thoroughly
- Then considered node expansion

### **Current approach:**
- Plotly already working ✅
- Add only real ERCOT nodes (not fake)
- Incremental: 4 nodes, test, maybe 1 more
- Maximum possible: 15 (ERCOT limit)

**Key insight:** We can't add 28 nodes because they don't exist in ERCOT's data. Maximum is 15.

---

## ✅ **Success Criteria**

- [ ] Added 4-5 nodes (maximum 15 total)
- [ ] All nodes show real ERCOT data
- [ ] Performance <3 seconds
- [ ] Tooltips work on all nodes
- [ ] Geographic coverage improved
- [ ] User toggle updated to reflect new counts
- [ ] Documented and tested

---

## 📝 **Next Steps**

1. Update `etl/ercot_lmp_etl.py` with 4 new nodes
2. Run ETL and verify data
3. Test dashboard performance
4. Run quality gate checklist
5. Decide whether to add 15th node
6. Update UI toggle labels
7. Merge to main if successful

---

**Status:** Ready to implement  
**Risk Level:** Low (only adding 5 nodes, all real data)  
**Expected Time:** 30-45 minutes  
**Rollback Plan:** Feature branch, easy to revert
