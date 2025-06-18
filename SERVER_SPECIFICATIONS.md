# Server Specifications for CircuitCLI Training

## 📊 **Dataset Context**
- **Images**: 2,424 circuit images
- **Annotations**: 196K annotations
- **Classes**: 54 electrical components
- **Dataset Size**: ~41MB (Train: 29MB, Val: 8.5MB, Test: 3.9MB)

## 🎯 **Recommended Server Configurations**

### 🥉 **Budget Server (Entry Level)**
**Cost**: $1,500 - $2,500 | **Training Time**: ~6-12 hours

#### Hardware Specs:
```
CPU:     AMD Ryzen 5 5600X (6 cores, 12 threads)
RAM:     32GB DDR4-3200
GPU:     NVIDIA RTX 3060 (12GB VRAM)
Storage: 1TB NVMe SSD
PSU:     650W 80+ Gold
Mobo:    B550 chipset
Case:    Mid-tower with good airflow
```

#### Performance Expectations:
- **Batch Size**: 16-24
- **Model Size**: YOLOv8n/s
- **Training Speed**: ~15-20 seconds/epoch
- **Total Training Time**: 6-8 hours (100 epochs)

#### Training Command:
```bash
python scripts/train_detector.py \
    --epochs 100 \
    --batch-size 16 \
    --model-size n \
    --use-wandb \
    --export-onnx
```

---

### 🥈 **Performance Server (Recommended)**
**Cost**: $3,000 - $5,000 | **Training Time**: ~3-5 hours

#### Hardware Specs:
```
CPU:     AMD Ryzen 7 5800X (8 cores, 16 threads)
RAM:     64GB DDR4-3200 (4x16GB)
GPU:     NVIDIA RTX 4070 Ti (12GB VRAM)
Storage: 2TB NVMe SSD (Gen4)
PSU:     750W 80+ Gold
Mobo:    X570 chipset
Case:    Full-tower with excellent cooling
```

#### Performance Expectations:
- **Batch Size**: 24-32
- **Model Size**: YOLOv8s/m
- **Training Speed**: ~8-12 seconds/epoch
- **Total Training Time**: 3-4 hours (100 epochs)

#### Training Command:
```bash
python scripts/train_detector.py \
    --epochs 150 \
    --batch-size 24 \
    --model-size s \
    --learning-rate 0.005 \
    --use-wandb \
    --export-onnx
```

---

### 🥇 **High-Performance Server (Professional)**
**Cost**: $6,000 - $10,000 | **Training Time**: ~1-2 hours

#### Hardware Specs:
```
CPU:     AMD Ryzen 9 5950X (16 cores, 32 threads)
RAM:     128GB DDR4-3200 (8x16GB)
GPU:     NVIDIA RTX 4090 (24GB VRAM)
Storage: 4TB NVMe SSD (Gen4) + 2TB backup SSD
PSU:     1000W 80+ Platinum
Mobo:    X570/B550 with PCIe 4.0
Cooling: AIO liquid cooling
Case:    Full-tower workstation
```

#### Performance Expectations:
- **Batch Size**: 32-64
- **Model Size**: YOLOv8m/l
- **Training Speed**: ~4-6 seconds/epoch
- **Total Training Time**: 1-2 hours (100 epochs)

#### Training Command:
```bash
python scripts/train_detector.py \
    --epochs 200 \
    --batch-size 32 \
    --model-size m \
    --learning-rate 0.003 \
    --use-wandb \
    --export-onnx
```

---

### 🚀 **Enterprise Server (Maximum Performance)**
**Cost**: $15,000 - $25,000 | **Training Time**: ~30-60 minutes

#### Hardware Specs:
```
CPU:     AMD Threadripper PRO 5975WX (32 cores, 64 threads)
RAM:     256GB DDR4-3200 ECC (8x32GB)
GPU:     NVIDIA RTX A6000 (48GB VRAM) or RTX 4090 x2
Storage: 8TB NVMe SSD RAID 0 + 4TB backup
PSU:     1600W 80+ Titanium
Mobo:    TRX50 workstation motherboard
Cooling: Custom liquid cooling loop
Case:    Rackmount 4U chassis
```

#### Performance Expectations:
- **Batch Size**: 64-128
- **Model Size**: YOLOv8l/x
- **Training Speed**: ~2-3 seconds/epoch
- **Total Training Time**: 30-45 minutes (100 epochs)

#### Training Command:
```bash
python scripts/train_detector.py \
    --epochs 300 \
    --batch-size 64 \
    --model-size l \
    --learning-rate 0.001 \
    --patience 100 \
    --use-wandb \
    --export-onnx
```

## 🌐 **Cloud Server Alternatives**

### AWS EC2 Instances

#### **Budget Option**: g4dn.xlarge
```
Specs:    4 vCPUs, 16GB RAM, T4 GPU (16GB)
Cost:     ~$0.526/hour (~$12.60/day)
Use Case: Testing and small experiments
```

#### **Recommended**: g4dn.2xlarge
```
Specs:    8 vCPUs, 32GB RAM, T4 GPU (16GB)
Cost:     ~$0.752/hour (~$18/day)
Use Case: Production training
```

#### **High Performance**: p3.2xlarge
```
Specs:    8 vCPUs, 61GB RAM, V100 GPU (16GB)
Cost:     ~$3.06/hour (~$73/day)
Use Case: Fast training, research
```

#### **Maximum Performance**: p4d.24xlarge
```
Specs:    96 vCPUs, 1152GB RAM, 8x A100 GPUs (40GB each)
Cost:     ~$32.77/hour (~$786/day)
Use Case: Large-scale training, multiple experiments
```

### Google Cloud Platform

#### **Budget**: n1-standard-4 + T4 GPU
```
Specs:    4 vCPUs, 15GB RAM, T4 GPU
Cost:     ~$0.50/hour
Use Case: Development and testing
```

#### **Recommended**: n1-standard-8 + V100 GPU
```
Specs:    8 vCPUs, 30GB RAM, V100 GPU
Cost:     ~$2.50/hour
Use Case: Production training
```

### Azure

#### **Budget**: Standard_NC6s_v3
```
Specs:    6 vCPUs, 112GB RAM, V100 GPU
Cost:     ~$3.06/hour
Use Case: Professional training
```

## 📈 **Performance Comparison Table**

| Configuration | GPU | VRAM | Batch Size | Training Time | Cost Range |
|---------------|-----|------|------------|---------------|------------|
| Budget | RTX 3060 | 12GB | 16 | 6-8 hours | $1,500-$2,500 |
| Performance | RTX 4070 Ti | 12GB | 24 | 3-4 hours | $3,000-$5,000 |
| High-Perf | RTX 4090 | 24GB | 32-64 | 1-2 hours | $6,000-$10,000 |
| Enterprise | A6000 | 48GB | 64-128 | 30-60 min | $15,000-$25,000 |
| AWS g4dn.2xl | T4 | 16GB | 20 | 4-5 hours | $18/day |
| AWS p3.2xl | V100 | 16GB | 24 | 2-3 hours | $73/day |

## 🎯 **Specific Recommendations by Use Case**

### 🔬 **Research & Development**
**Recommended**: Performance Server (RTX 4070 Ti)
- Multiple experiments per day
- Good balance of cost and performance
- Sufficient for model variations

### 🏭 **Production Deployment**
**Recommended**: High-Performance Server (RTX 4090)
- Fast iteration cycles
- Reliable hardware
- Good for continuous training

### 🏢 **Enterprise/Commercial**
**Recommended**: Enterprise Server or Cloud
- Multiple simultaneous experiments
- Scalable infrastructure
- Professional support

### 💰 **Startup/Budget Constrained**
**Recommended**: Budget Server or Cloud spot instances
- Cost-effective training
- Acceptable training times
- Upgrade path available

## ⚡ **Performance Optimization Tips**

### For Your Dataset (2,424 images):
1. **Batch Size Optimization**:
   - RTX 3060: Use batch size 16
   - RTX 4070 Ti: Use batch size 24-32
   - RTX 4090: Use batch size 32-64

2. **Model Size Selection**:
   - Start with YOLOv8n for prototyping
   - Use YOLOv8s for production
   - Only use YOLOv8m/l if you have RTX 4090+

3. **Training Strategy**:
   - 100 epochs minimum for good results
   - 200-300 epochs for best accuracy
   - Use early stopping (patience=50)

## 🛠 **Server Setup Checklist**

### Hardware Assembly:
- [ ] Install CPU with proper thermal paste
- [ ] Install RAM in correct slots (check motherboard manual)
- [ ] Install GPU in PCIe x16 slot
- [ ] Connect all power cables (24-pin, 8-pin CPU, GPU power)
- [ ] Ensure adequate cooling (case fans, CPU cooler)

### Software Setup:
- [ ] Install Ubuntu 20.04/22.04 LTS
- [ ] Install NVIDIA drivers (latest stable)
- [ ] Install CUDA toolkit (11.8 or 12.1)
- [ ] Install Python 3.9+
- [ ] Run CircuitCLI setup script

### Verification Commands:
```bash
# Check GPU
nvidia-smi

# Check CUDA
nvcc --version

# Test PyTorch GPU
python -c "import torch; print(torch.cuda.is_available())"

# Run CircuitCLI test
python scripts/train_detector.py --epochs 1 --batch-size 2
```

## 💡 **Cost-Saving Tips**

1. **Cloud Spot Instances**: 50-90% cheaper than on-demand
2. **Used Hardware**: RTX 3080/3090 still excellent for training
3. **Shared Cloud GPUs**: Services like Vast.ai, RunPod
4. **Local University**: Many have GPU clusters available
5. **Google Colab Pro**: $10/month for occasional training

## 🔧 **Maintenance & Monitoring**

### Temperature Monitoring:
```bash
# GPU temperature
nvidia-smi -l 1

# CPU temperature
sensors
```

### Performance Monitoring:
```bash
# GPU utilization
watch -n 1 nvidia-smi

# System resources
htop

# Training progress
tensorboard --logdir runs/
```

## 📋 **Final Recommendation**

For your CircuitCLI project with 2,424 images:

**Best Value**: **Performance Server (RTX 4070 Ti)** - $3,000-$5,000
- Perfect balance of cost and performance
- 3-4 hour training time is very reasonable
- Can handle multiple experiments per day
- Future-proof for larger datasets

**Cloud Alternative**: **AWS g4dn.2xlarge** - ~$18/day
- No upfront hardware cost
- Pay only when training
- Easy to scale up/down as needed

The training will be efficient and cost-effective with either option! 