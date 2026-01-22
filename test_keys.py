#!/usr/bin/env python3
"""Test script to debug keyboard detection"""
from pynput import keyboard

def on_press(key):
    try:
        print(f"Pressed: {key}")
    except:
        print(f"Pressed: {key}")

def on_release(key):
    print(f"Released: {key}")
    if key == keyboard.Key.esc:
        print("ESC pressed - exiting")
        return False

print("Press any keys to test detection (ESC to quit)...")
print("Try pressing Ctrl, Alt, and other keys to see if they are detected.\n")

with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()
