# Architecture

## Overview

NeuroGain's backend is a stateless-per-request pose analysis API. Each exercise has its own analyzer class that owns a MediaPipe `Pose` instance and its own rep-counting state (current stage, rep count, frame count). The Flutter client streams individual camera frames to the matching `/analyze/<exercise>` endpoint; the analyzer returns the current rep count and short-form feedback for that frame.

## Why per-frame, not per-video

Analyzing single frames (rather than buffering a clip) keeps latency low enough for real-time feedback during a live set, and keeps the backend stateless across requests aside from the in-memory analyzer instance — simpler to reason about and deploy on a small Hugging Face Space instance.

## Rep counting

Each exercise analyzer converts landmark positions into one or more joint angles relevant to that movement (e.g. shoulder–elbow–wrist for a curl), then runs a small state machine over those angles: crossing a "contracted" threshold moves the stage to `UP`, crossing an "extended" threshold on the way back down counts a completed rep. This pattern is shared across all five exercises — what differs per exercise is which joints are tracked and what counts as a valid range of motion, which is deliberately not detailed here.

## Visibility guarding

Before trusting any angle calculation, the analyzer checks MediaPipe's per-landmark visibility score for the joints it needs. If key joints fall below the confidence threshold (e.g. the user has stepped out of frame or is occluded), the analyzer skips the angle math and returns a "move into frame" prompt instead of a potentially garbage rep count.

## Persistence

Rep counts are held in memory for the duration of a set. When the user finishes a set, the client calls the exercise's `/reset` endpoint, which packages the completed set (exercise name, rep count, timestamp) and POSTs it to the MeisterFit web backend for storage against the user's history, then resets the in-memory counter for the next set.

## Deployment

The FastAPI backend runs on a Hugging Face Space. Workout persistence is handled by a separate Vercel-hosted service, decoupling the pose-analysis compute from the data layer.
