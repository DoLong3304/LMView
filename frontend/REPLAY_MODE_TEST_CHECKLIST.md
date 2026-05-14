# Replay Mode - Manual Testing Checklist

## Test Environment
- **Dev Server**: http://localhost:3001
- **Backend API**: http://localhost:8080
- **Browser**: Chrome/Edge (recommended)

## Prerequisites
✅ Backend services running (docker-compose up)
✅ Dev server running (npm run dev)
✅ Chart loaded with historical data

---

## Test Cases

### 1. Enter Replay Selection Mode
**Steps:**
1. Click "Replay Mode" button in toolbar
2. Observe cursor changes to selection mode
3. Observe "Click on a candle to start replay" message

**Expected:**
- ✅ Button highlights/changes state
- ✅ Cursor changes to crosshair/selection cursor
- ✅ Instruction message appears
- ✅ Active tool switches to 'cursor'

---

### 2. Start Replay from Selected Candle
**Steps:**
1. Enter replay selection mode
2. Click on a candle in the middle of the chart
3. Observe chart updates

**Expected:**
- ✅ Chart clears and shows only the selected candle
- ✅ Replay controls panel appears (floating bottom-center)
- ✅ Replay is paused by default
- ✅ Counter shows "1 / N" (where N = total candles from selected point)
- ✅ WebSocket updates are blocked (no new live data)

---

### 3. Play/Pause Controls
**Steps:**
1. Start replay from a candle
2. Click "Play" button
3. Observe candles advancing automatically
4. Click "Pause" button
5. Observe playback stops

**Expected:**
- ✅ Play button changes to Pause icon
- ✅ Candles advance one by one at 1x speed (1 candle/second)
- ✅ Counter increments: "2 / N", "3 / N", etc.
- ✅ Progress bar fills gradually
- ✅ Pause button stops playback immediately
- ✅ Chart freezes at current candle

---

### 4. Step Forward (Manual Advance)
**Steps:**
1. Start replay and pause
2. Click "Step Forward" button multiple times
3. Observe each click advances 1 candle

**Expected:**
- ✅ Each click advances exactly 1 candle
- ✅ Counter increments by 1
- ✅ Progress bar updates
- ✅ Button is disabled when playing

---

### 5. Playback Speed Control
**Steps:**
1. Start replay and play
2. Change speed to 3x
3. Observe faster playback
4. Change to 10x
5. Change to 100x
6. Change back to 1x

**Expected:**
- ✅ 1x: 1 candle per second
- ✅ 3x: ~3 candles per second
- ✅ 10x: ~10 candles per second
- ✅ 100x: ~100 candles per second (very fast)
- ✅ Speed change takes effect immediately
- ✅ Playback continues smoothly after speed change

---

### 6. Reach End of Replay
**Steps:**
1. Start replay from near the end (last 5 candles)
2. Play until reaching the last candle
3. Observe behavior

**Expected:**
- ✅ Playback stops automatically at last candle
- ✅ Play button becomes disabled or shows "Ended" state
- ✅ Counter shows "N / N"
- ✅ Progress bar is 100% filled
- ✅ No errors in console

---

### 7. Exit Replay Mode
**Steps:**
1. Start replay and play for a few candles
2. Click "Exit" button in replay controls
3. Observe chart restoration

**Expected:**
- ✅ Replay controls panel disappears
- ✅ Chart restores full historical data
- ✅ WebSocket reconnects and live data resumes
- ✅ "Replay Mode" button returns to normal state
- ✅ Can draw/interact with chart normally

---

### 8. Cancel Selection Mode
**Steps:**
1. Click "Replay Mode" button to enter selection
2. Click "Replay Mode" button again (or press Esc)
3. Observe selection mode exits

**Expected:**
- ✅ Selection mode exits
- ✅ Cursor returns to normal
- ✅ Instruction message disappears
- ✅ No replay starts

---

### 9. WebSocket Blocking Verification
**Steps:**
1. Start replay and play
2. Open browser DevTools → Network tab
3. Observe WebSocket connections
4. Wait for live data updates (should not happen)
5. Exit replay
6. Observe WebSocket reconnects

**Expected:**
- ✅ During replay: No WebSocket messages received
- ✅ During replay: No polling requests
- ✅ After exit: WebSocket reconnects immediately
- ✅ After exit: Live data resumes updating chart

---

### 10. Edge Cases

#### 10.1 Start Replay from First Candle
**Steps:**
1. Click on the very first candle
2. Start replay

**Expected:**
- ✅ Replay starts with all historical data
- ✅ Counter shows "1 / N" where N = total candles

#### 10.2 Start Replay from Last Candle
**Steps:**
1. Click on the last candle
2. Start replay

**Expected:**
- ✅ Replay starts with only 1 candle
- ✅ Counter shows "1 / 1"
- ✅ Play button is disabled (already at end)

#### 10.3 Rapid Speed Changes
**Steps:**
1. Start replay and play
2. Rapidly change speed: 1x → 3x → 10x → 1x → 100x

**Expected:**
- ✅ No crashes or errors
- ✅ Speed changes smoothly
- ✅ No duplicate candles
- ✅ No skipped candles

#### 10.4 Exit During Playback
**Steps:**
1. Start replay and play at 100x speed
2. Immediately click "Exit"

**Expected:**
- ✅ Playback stops immediately
- ✅ Chart restores correctly
- ✅ No memory leaks (check DevTools Memory)

---

## Console Logs to Verify

During testing, check browser console for these logs:

```
[useReplayMode] Replay initialized with N candles, starting at index 0
[useReplayMode] Playing at 1x speed (1000ms interval)
[useReplayMode] Paused
[useReplayMode] Speed changed to 3x
[useReplayMode] Replay ended
[useReplayMode] Exited replay mode
```

---

## Known Issues / Limitations

1. **No progress bar scrubbing**: Cannot click on progress bar to jump to specific candle
2. **No keyboard shortcuts**: Must use mouse to control replay
3. **No replay speed input**: Only predefined speeds (1x, 3x, 10x, 100x)
4. **No reverse playback**: Can only play forward

---

## Performance Benchmarks

- **Chart update latency**: < 16ms per candle (60 FPS)
- **Memory usage**: Should not increase significantly during replay
- **CPU usage**: Should remain < 30% at 100x speed

---

## Accessibility

- [ ] Keyboard navigation works (Tab, Enter, Space)
- [ ] Screen reader announces state changes
- [ ] Focus indicators visible
- [ ] Color contrast meets WCAG AA

---

## Browser Compatibility

Test on:
- [ ] Chrome 120+
- [ ] Edge 120+
- [ ] Firefox 120+
- [ ] Safari 17+

---

## Test Results

| Test Case | Status | Notes |
|-----------|--------|-------|
| 1. Enter Selection Mode | ⏳ | |
| 2. Start Replay | ⏳ | |
| 3. Play/Pause | ⏳ | |
| 4. Step Forward | ⏳ | |
| 5. Speed Control | ⏳ | |
| 6. Reach End | ⏳ | |
| 7. Exit Replay | ⏳ | |
| 8. Cancel Selection | ⏳ | |
| 9. WebSocket Blocking | ⏳ | |
| 10. Edge Cases | ⏳ | |

**Legend:**
- ⏳ Not tested
- ✅ Pass
- ❌ Fail
- ⚠️ Partial pass (with notes)

---

## Bug Report Template

If you find a bug, report it with:

```
**Bug Title**: [Short description]

**Steps to Reproduce**:
1. 
2. 
3. 

**Expected Behavior**:


**Actual Behavior**:


**Console Errors**:


**Screenshots**:


**Environment**:
- Browser: 
- OS: 
- Backend version: 
```
