#!/usr/bin/python
import sys, re

# the doc for the MT protocol can be found here:
# https://www.kernel.org/doc/Documentation/input/multi-touch-protocol.txt


# A type A multi-touch screen
class MultiTouchTypeAParser:
    pass # TODO

# A type B multi-touch screen
# a list of supported features:
# MT_PRESSURE, MT_POSITION_X, MT_POSITION_Y, TRAKCING_ID, SLOT, TOUCH_MAJOR
# unsupported:
# ABS_MT_TOUCH_MINOR, ABS_MT_WIDTH_MAJOR, ABS_MT_WIDTH_MINOR, ABS_MT_DISTANCE
# ABS_MT_ORIENTATION, ABS_MT_TOOL_X, ABS_MT_TOOL_Y
class MultiTouchTypeBParser:
    NAVIGATION_HEIGHT = 48 # the standard navigation bar at the bottom
    def __init__(self):
        # states
        self.currentSlotIndex = 0
        self.currentSlot = self.genNewSlot()
        self.slots = [self.currentSlot]
    def genNewSlot(self):
        return { "x" : 0, "y" : 0, "pressure" : 0, "tracking_id" : 0xFFFFFFFF, "touch_major" : 0}
    def process(self, tp, reporter):
        (timestamp, evType, evCmd, evVal) = tp
        if evType == "EV_ABS":
            if evCmd == "ABS_MT_SLOT":
                self.currentSlotIndex = evVal
                if evVal >= len(self.slots):
                    self.slots.extend([None]*(evVal + 1 - len(self.slots)))
                    self.slots[evVal] = self.genNewSlot()
                self.currentSlot = self.slots[self.currentSlotIndex]
            elif evCmd == "ABS_MT_POSITION_X":
                self.currentSlot["x"] = evVal
            elif evCmd == "ABS_MT_POSITION_Y":
                self.currentSlot["y"] = evVal
            elif evCmd == "ABS_MT_TRACKING_ID":
                if evVal == 0xFFFFFFFF:
                    # unbinding
                    self.slots[self.currentSlotIndex] = self.genNewSlot()
                else:
                    # binding tracking_id to slot
                    self.currentSlot["tracking_id"] = evVal
            elif evCmd == "ABS_MT_PRESSURE":
                self.currentSlot["pressure"] = evVal
            elif evCmd == "ABS_MT_TOUCH_MAJOR":
                self.currentSlot["touch_major"] = evVal
            else:
                print "[WARN] MTDriver meets unknown evCmd" + str(tp)
        elif evType == "EV_SYN":
            if evCmd == "SYN_REPORT":
                for ev in self.slots:
                    if ev["tracking_id"] != 0xFFFFFFFF:
                        reporter.report(timestamp, # current timestamp
                            ev["tracking_id"], # this specifies which finger
                            ev["touch_major"], # the diameter of the touch
                            ev["x"], # the X coordinate, in pixel
                            ev["y"], # the Y coordinate , in pixel
                            ev["pressure"]) # the pressure
            else:
                print "[WARN] MTDriver meets unknwon evCmd" + str(tp)
        else:
            print "[WARN] MTDriver skips unknown line:" + str(tp)

# provide an interface like the MotionEvent in Android
class MultiTouchRecorder:
    def report(self, timstamp, tracking_id, touch_major, x, y, pressure):
        tp = (timstamp, tracking_id, touch_major, x, y, pressure)
        print tp
    
def processRawTrace(tracePath, myHandlers, evDev):
    pattern = re.compile("\\[\s*(\d+\.\d+)\\]\s*(\w+)\s*(\w+)\s*(\w+)")
    fp = open(tracePath)
    for (i, line) in enumerate(fp):
        # a line is in the format of:
        # "time(float) evType(str) evCmd(str) evVal(int)"
        # refer to Linux evdev for details
        # here we assume the line is a readable dump from getevent
        m = pattern.match(line)
        timestamp = float(m.group(1))
        evType = m.group(2)
        evCmd = m.group(3)
        evVal = int(m.group(4), 16)
        tp = (timestamp, evType, evCmd, evVal)
        # find the corresponding driver for this component
        if evDev in myHandlers:
            (driver, reporter) = myHandlers[evDev];
            driver.process(tp, reporter)
        else:
            print "[WARN] Unknown device: " + str(tp)

def main():
    if len(sys.argv) <= 1:
        print "Usage: python test.py TRACE_PATH"
        print "The trace must be generated from getevent -lp [EVDEV]"
        return 1

    # TODO: now hardcoded, a mapping from a evDev to its handlers
    # for each device, we need one parser and one reporter
    myHandlers = {"/dev/input1" : (MultiTouchTypeBParser(), MultiTouchRecorder())}
    print ("timestamp", "tracking_id", "touch_major", "x", "y", "pressure")
    processRawTrace(sys.argv[1], myHandlers, "/dev/input1")

if __name__ == "__main__":
    main()