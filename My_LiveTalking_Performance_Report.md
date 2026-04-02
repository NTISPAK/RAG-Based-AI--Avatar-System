# LiveTalking Performance Optimization Report
## Week of March 22-28, 2026

---

## 🎯 Executive Summary

This week, I focused on optimizing the LiveTalking avatar system to improve performance on existing hardware. Through systematic code analysis and targeted improvements, I implemented optimizations aimed at increasing FPS and reducing latency.

---

## 📊 Performance Optimizations Applied

| Component | Optimization | Expected Impact |
|-----------|-------------|-----------------|
| **Face Processing** | Pre-computed tensors | Reduced per-batch overhead |
| **Audio Timing** | Timeout reduction (10ms → 2ms) | Faster idle loop processing |
| **Queue Management** | Adjusted backpressure thresholds | Smoother frame delivery |
| **Memory Buffers** | Increased buffer sizes | Reduced blocking |

---

## 🔍 Performance Analysis

### Code Review Process

I analyzed the codebase to identify performance bottlenecks in the inference pipeline:

1. **Audio Frame Timeout**: Found 10ms timeout being called 8 times per batch (80ms total during silence)
2. **Face Image Processing**: Identified repeated numpy operations (copy, mask, concatenate, normalize, transpose) on each batch
3. **Queue Backpressure**: Observed aggressive throttling starting at queue size 5

### Findings

The analysis revealed opportunities to optimize the inference loop, audio processing, and queue management.

---

## 🚀 Optimizations Implemented

### Optimization 1: Pre-computed Face Tensors

**Implementation:**
Modified `load_avatar()` to pre-process all 550 face frames at startup:
- Mask creation
- Concatenation with original
- Normalization to float32
- Conversion to PyTorch tensors on device

**Changes:**
- Updated `lipreal.py` to use pre-computed `face_tensor_stack`
- Modified inference loop to use direct tensor indexing instead of per-batch numpy operations
- Changed from `torch.no_grad()` to `torch.inference_mode()`

### Optimization 2: Audio Frame Timeout Reduction

**Implementation:**
Modified `baseasr.py` timeout parameter:
```python
# Before: timeout=0.01 (10ms)
# After: timeout=0.002 (2ms)
```

**Rationale:**
Reduces cumulative wait time during silence periods (8 calls per batch).

### Optimization 3: Queue Management Adjustments

**Implementation:**
Updated backpressure logic in `lipreal.py`:
- Increased threshold from queue size 5 to 8
- Reduced sleep multiplier from 0.6 to 0.4
- Increased `res_frame_queue` buffer from `batch_size*2` to `batch_size*4`

**Changes to `webrtc.py`:**
- Reduced WebRTC queue from 30 to 20 frames for lower latency

---

## 🎪 Hardware Considerations

### Current Development System (Mac M2 MPS)
- Testing performed on Mac M2 with MPS backend
- Optimizations target reduction in CPU/GPU overhead
- Pre-computed tensors reduce per-frame processing

### Production System Projections (GTX 1660)
- CUDA backend expected to be faster than MPS
- GTX 1660 has 1408 CUDA cores, 6GB VRAM
- Optimizations should benefit CUDA performance as well

---

## 📈 Testing Status

### Deployment
- System deployed with optimizations applied
- RAG backend running on port 8000
- LiveTalking frontend running on port 8010
- Pre-computed face tensors confirmed loading (550 frames on MPS)

### Performance Monitoring
- FPS logging enabled in inference loop
- Logs show `------actual avg infer fps:` after 100 frames processed
- Further testing needed to validate performance improvements under various scenarios

---

## 💡 Key Technical Changes

### Pre-computed Tensor Architecture
- Moved face image processing from runtime to startup
- Eliminates repeated numpy operations during inference
- Tensors stored on device for direct access

### Timeout Optimization
- Reduced audio frame timeout from 10ms to 2ms
- Decreases idle loop latency during silence periods
- Maintains responsiveness for actual audio data

### Queue Tuning
- Adjusted backpressure thresholds and sleep parameters
- Increased buffer sizes to reduce blocking
- Balanced throughput with latency

---

## 🏆 Expected Benefits

### Performance Improvements
- Reduced per-batch processing overhead
- Faster idle loop during conversation pauses
- Smoother frame delivery with adjusted backpressure

### Technical Benefits
- Cleaner inference pipeline with pre-computed data
- Reduced runtime allocations and processing
- Better separation of startup vs runtime work

### Scalability
- Optimizations apply to different hardware configurations
- Foundation for future CUDA-specific improvements (FP16, larger batches)
- No hardware upgrades required for current optimizations

---

## 📋 Implementation Timeline

| Phase | Work Performed |
|-------|---------------|
| **Analysis** | Code review of lipreal.py, baseasr.py, webrtc.py, basereal.py |
| **Implementation** | Modified load_avatar(), inference(), timeout values, queue parameters |
| **Testing** | Deployed system with optimizations, verified startup logs |
| **Documentation** | Created this report documenting changes |

**Project Duration**: Week of March 22-28, 2026

---

## 🎉 Summary

This week, I implemented performance optimizations for the LiveTalking system:

1. **Pre-computed face tensors** to eliminate runtime processing overhead
2. **Reduced audio timeout** from 10ms to 2ms for faster idle loops
3. **Adjusted queue management** for better frame pacing
4. **Increased buffer sizes** to reduce blocking
5. **Applied torch.inference_mode()** for slightly better inference performance

These optimizations target the main bottlenecks identified in the inference pipeline and should improve overall system responsiveness.

---

## 🌟 Future Optimization Opportunities

### Potential Next Steps
- **CUDA FP16 inference** for NVIDIA GPU systems
- **Adaptive batch sizing** based on available GPU memory
- **Further queue tuning** based on real-world usage patterns

### Long-term Possibilities
- Model quantization for edge deployment
- Multi-GPU support for concurrent sessions
- Additional caching strategies

---

## 📊 Technical Details

**Files Modified:**
- `LiveTalking/lipreal.py` - Pre-computed tensors, inference optimization, backpressure
- `LiveTalking/baseasr.py` - Audio timeout reduction
- `LiveTalking/webrtc.py` - Queue size adjustment

**Optimization Techniques Applied:**
- Pre-computed tensor architecture
- Timeout parameter tuning
- Queue threshold adjustments
- Buffer size increases
- Inference mode optimization

**Testing Environment:**
- Mac M2 with MPS backend
- Python 3.11
- PyTorch with MPS support

---

## 🎯 Conclusion

This week, I focused on optimizing the LiveTalking avatar system by identifying and addressing performance bottlenecks in the inference pipeline. The main optimizations include:

- Pre-computing face tensors to eliminate runtime overhead
- Reducing audio frame timeout to speed up idle loops
- Adjusting queue management for smoother frame delivery

The system is now deployed with these optimizations. Further testing and monitoring will help validate the actual performance improvements in real-world usage scenarios.

---

*Report Date: March 28, 2026*
*Project: LiveTalking Performance Optimization*
*Focus: Inference pipeline, audio processing, queue management*
