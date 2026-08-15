# 🧮 Hands-On Lesson: CIDR, Subnet Masks, and Network Ranges

**Audience:** Networking certification students  
**Duration:** 90-120 minutes  
**Topic:** CIDR notation, subnet masks, network ranges, usable host addresses, broadcast addresses, and basic segmentation

## 🎯 Learning Goals

By the end of this lesson, students should be able to:

- Explain CIDR notation.
- Convert common CIDR prefixes to subnet masks.
- Identify the network address.
- Identify the broadcast address.
- Find the first and last usable IP address.
- Calculate the number of usable hosts.
- Show the network bits, host bits, and subnet mask in binary.
- Understand how subnetting supports network segmentation.

## 🔑 Key Terms

| Term | Meaning |
|---|---|
| IP address | A unique address assigned to a host |
| Subnet mask | Defines which part of the IP is network and which part is host |
| CIDR | Short notation for subnet mask, such as `/24` |
| Network address | First address in the subnet; identifies the subnet |
| Broadcast address | Last address in the subnet; used to reach all hosts in that subnet |
| Usable host range | IP addresses that can be assigned to devices |
| Segmentation | Dividing a network into smaller networks |

## 🧠 Part 1: Understanding CIDR

CIDR tells us how many bits are used for the network portion of an IP address.

Example:

```text
192.168.1.0/24
```

The `/24` means the first 24 bits are the network portion.

IPv4 addresses have 32 bits total.

```text
Network bits + Host bits = 32
```

For `/24`:

```text
32 - 24 = 8 host bits
```

## 🎭 Part 2: Common CIDR Masks

| CIDR | Subnet Mask | Total Addresses | Usable Hosts |
|---|---|---:|---:|
| /8 | 255.0.0.0 | 16,777,216 | 16,777,214 |
| /16 | 255.255.0.0 | 65,536 | 65,534 |
| /24 | 255.255.255.0 | 256 | 254 |
| /25 | 255.255.255.128 | 128 | 126 |
| /26 | 255.255.255.192 | 64 | 62 |
| /27 | 255.255.255.224 | 32 | 30 |
| /28 | 255.255.255.240 | 16 | 14 |
| /29 | 255.255.255.248 | 8 | 6 |
| /30 | 255.255.255.252 | 4 | 2 |

## 🔢 Part 3: Binary Math: Network Bits, Host Bits, and Masks

IPv4 addresses are 32 bits long. A subnet mask uses `1` bits for the network portion and `0` bits for the host portion.

Example mask:

```text
/19 mask:
11111111 11111111 11100000 00000000
```

That equals:

```text
255.255.224.0
```

Now use that `/19` mask with an IP address:

```text
IP address: 172.16.70.45/19
Subnet mask: 255.255.224.0
```

Binary:

```text
IP:      10101100 00010000 01000110 00101101
Mask:    11111111 11111111 11100000 00000000
         NNNNNNNN NNNNNNNN NNNHHHHH HHHHHHHH
```

The first 19 bits are the network part. The remaining 13 bits are the host part.

Focus on the third octet because that is where the mask changes:

```text
IP third octet:    01000110 = 70
Mask third octet:  11100000 = 224
Network result:    01000000 = 64
```

So:

```text
Network address:   172.16.64.0
Broadcast address: 172.16.95.255
```

Why does it end at `95`?

```text
Block size = 256 - 224 = 32
Subnet starts: 0, 32, 64, 96, 128, 160, 192, 224
```

Since `70` falls between `64` and `95`, the subnet is:

```text
172.16.64.0 - 172.16.95.255
```

Result:

| Item | Value |
|---|---|
| Network bits | 19 |
| Host bits | 13 |
| Subnet mask | 255.255.224.0 |
| Network address | 172.16.64.0 |
| First usable IP | 172.16.64.1 |
| Last usable IP | 172.16.95.254 |
| Broadcast address | 172.16.95.255 |

### Simple Binary Reference

| Decimal | Binary |
|---:|---|
| 255 | 11111111 |
| 254 | 11111110 |
| 252 | 11111100 |
| 248 | 11111000 |
| 240 | 11110000 |
| 224 | 11100000 |
| 192 | 11000000 |
| 128 | 10000000 |
| 0 | 00000000 |

### Example 1: 10 Network

```text
IP address: 10.25.14.8/16
Subnet mask: 255.255.0.0
```

Binary:

```text
IP:   00001010 00011001 00001110 00001000
Mask: 11111111 11111111 00000000 00000000
      NNNNNNNN NNNNNNNN HHHHHHHH HHHHHHHH
```

Result:

| Item | Value |
|---|---|
| Network part | 10.25 |
| Host part | 14.8 |
| Network address | 10.25.0.0 |
| Broadcast address | 10.25.255.255 |
| First usable IP | 10.25.0.1 |
| Last usable IP | 10.25.255.254 |

### Example 2: 172.16 Network

```text
IP address: 172.16.35.90/20
Subnet mask: 255.255.240.0
```

Binary:

```text
IP:   10101100 00010000 00100011 01011010
Mask: 11111111 11111111 11110000 00000000
      NNNNNNNN NNNNNNNN NNNNHHHH HHHHHHHH
```

The third octet is `35`. With a `/20`, the block size is:

```text
256 - 240 = 16
```

The subnet ranges in the third octet are:

```text
0, 16, 32, 48, 64, ...
```

`35` belongs in the `32` subnet.

Result:

| Item | Value |
|---|---|
| Network part | 172.16.32 |
| Host part | Host bits inside 35.90 |
| Network address | 172.16.32.0 |
| Broadcast address | 172.16.47.255 |
| First usable IP | 172.16.32.1 |
| Last usable IP | 172.16.47.254 |

### Example 3: 192.168 Network

```text
IP address: 192.168.10.75/27
Subnet mask: 255.255.255.224
```

Binary:

```text
IP:   11000000 10101000 00001010 01001011
Mask: 11111111 11111111 11111111 11100000
      NNNNNNNN NNNNNNNN NNNNNNNN NNNHHHHH
```

The fourth octet is `75`. With a `/27`, the block size is:

```text
256 - 224 = 32
```

The subnet ranges in the fourth octet are:

```text
0, 32, 64, 96, 128, 160, 192, 224
```

`75` belongs in the `64` subnet.

Result:

| Item | Value |
|---|---|
| Network part | 192.168.10.64 |
| Host part | Host bits inside last octet |
| Network address | 192.168.10.64 |
| Broadcast address | 192.168.10.95 |
| First usable IP | 192.168.10.65 |
| Last usable IP | 192.168.10.94 |

## 🧮 Part 4: Host Calculation Formula

To calculate total addresses:

```text
2 ^ number of host bits
```

To calculate usable host addresses:

```text
2 ^ number of host bits - 2
```

The `-2` removes:

- Network address
- Broadcast address

Example:

```text
192.168.1.0/24
```

Host bits:

```text
32 - 24 = 8
```

Total addresses:

```text
2 ^ 8 = 256
```

Usable hosts:

```text
256 - 2 = 254
```

## 📍 Part 5: Finding the Network Range

Example:

```text
192.168.1.0/24
```

Result:

| Item | Value |
|---|---|
| Network address | 192.168.1.0 |
| First usable IP | 192.168.1.1 |
| Last usable IP | 192.168.1.254 |
| Broadcast address | 192.168.1.255 |
| Subnet mask | 255.255.255.0 |
| Usable hosts | 254 |

## 📦 Part 6: Block Size Method

For many certification questions, the block size method is fast.

Use this formula:

```text
Block size = 256 - subnet mask value in the interesting octet
```

Example:

```text
192.168.1.0/26
```

`/26` equals:

```text
255.255.255.192
```

Interesting octet:

```text
192
```

Block size:

```text
256 - 192 = 64
```

The networks increase by 64:

```text
192.168.1.0
192.168.1.64
192.168.1.128
192.168.1.192
```

So the `/26` subnets are:

| Network | First Usable | Last Usable | Broadcast |
|---|---|---|---|
| 192.168.1.0/26 | 192.168.1.1 | 192.168.1.62 | 192.168.1.63 |
| 192.168.1.64/26 | 192.168.1.65 | 192.168.1.126 | 192.168.1.127 |
| 192.168.1.128/26 | 192.168.1.129 | 192.168.1.190 | 192.168.1.191 |
| 192.168.1.192/26 | 192.168.1.193 | 192.168.1.254 | 192.168.1.255 |

## 📝 Part 7: Worked Example

Question:

```text
Find the network address, first usable IP, last usable IP, broadcast address, and usable host count for:

192.168.10.75/27
```

Step 1: Find the subnet mask.

```text
/27 = 255.255.255.224
```

Step 2: Find the block size.

```text
256 - 224 = 32
```

Step 3: List the subnet ranges.

```text
192.168.10.0
192.168.10.32
192.168.10.64
192.168.10.96
192.168.10.128
192.168.10.160
192.168.10.192
192.168.10.224
```

Step 4: Find where `192.168.10.75` belongs.

It falls between:

```text
192.168.10.64 and 192.168.10.95
```

Answer:

| Item | Value |
|---|---|
| Network address | 192.168.10.64 |
| First usable IP | 192.168.10.65 |
| Last usable IP | 192.168.10.94 |
| Broadcast address | 192.168.10.95 |
| Subnet mask | 255.255.255.224 |
| Usable hosts | 30 |

## 🧩 Part 8: Segmentation Example

A company has this network:

```text
192.168.20.0/24
```

They need to segment it into four departments:

- Admin
- Sales
- IT
- Guest Wi-Fi

To create 4 equal subnets from a `/24`, borrow 2 bits:

```text
/24 + 2 = /26
```

Each `/26` subnet has:

```text
64 total addresses
62 usable hosts
```

Segmentation plan:

| Department | Network | Usable Range | Broadcast |
|---|---|---|---|
| Admin | 192.168.20.0/26 | 192.168.20.1 - 192.168.20.62 | 192.168.20.63 |
| Sales | 192.168.20.64/26 | 192.168.20.65 - 192.168.20.126 | 192.168.20.127 |
| IT | 192.168.20.128/26 | 192.168.20.129 - 192.168.20.190 | 192.168.20.191 |
| Guest Wi-Fi | 192.168.20.192/26 | 192.168.20.193 - 192.168.20.254 | 192.168.20.255 |

## ❓ Student Questions

### 🔎 Question Type 1: Identify CIDR Information

For each network, identify the subnet mask and usable host count.

```text
1. 192.168.1.0/24
2. 10.10.10.0/25
3. 172.16.5.0/26
4. 192.168.50.0/27
5. 10.1.1.0/28
```

### 📍 Question Type 2: Find Network Range

For each IP address, find:

- Network address
- First usable IP
- Last usable IP
- Broadcast address

```text
1. 192.168.1.45/26
2. 192.168.5.130/25
3. 10.0.0.77/27
4. 172.16.10.200/28
5. 192.168.100.14/29
```

### ✅ Question Type 3: Choose the Best Subnet

Choose the smallest subnet that supports the required number of hosts.

```text
1. 50 hosts
2. 100 hosts
3. 25 hosts
4. 12 hosts
5. 2 hosts
```

### 🧩 Question Type 4: Segment a Network

Segment this network into 4 equal subnets:

```text
192.168.30.0/24
```

For each subnet, list:

- Network address
- First usable IP
- Last usable IP
- Broadcast address

### 🛠️ Question Type 5: Troubleshooting Address Assignment

A device has this configuration:

```text
IP address: 192.168.40.130
Subnet mask: 255.255.255.192
Default gateway: 192.168.40.1
```

Questions:

1. What is the device's network address?
2. What is the usable range?
3. Is the default gateway in the same subnet?
4. What is the likely problem?

### 🔢 Question Type 6: Binary Math

For each item, write the subnet mask in binary and mark the network and host portions.

```text
1. 10.20.30.40/16
2. 172.16.50.100/20
3. 192.168.5.130/25
4. 192.168.10.75/27
5. 10.1.2.3/8
```

For each item, also find:

- Network address
- Broadcast address
- First usable IP
- Last usable IP

## 🗝️ Answer Key

### 🔎 Answer Type 1

| Network | Subnet Mask | Usable Hosts |
|---|---|---:|
| 192.168.1.0/24 | 255.255.255.0 | 254 |
| 10.10.10.0/25 | 255.255.255.128 | 126 |
| 172.16.5.0/26 | 255.255.255.192 | 62 |
| 192.168.50.0/27 | 255.255.255.224 | 30 |
| 10.1.1.0/28 | 255.255.255.240 | 14 |

### 📍 Answer Type 2

| IP/CIDR | Network | First Usable | Last Usable | Broadcast |
|---|---|---|---|---|
| 192.168.1.45/26 | 192.168.1.0 | 192.168.1.1 | 192.168.1.62 | 192.168.1.63 |
| 192.168.5.130/25 | 192.168.5.128 | 192.168.5.129 | 192.168.5.254 | 192.168.5.255 |
| 10.0.0.77/27 | 10.0.0.64 | 10.0.0.65 | 10.0.0.94 | 10.0.0.95 |
| 172.16.10.200/28 | 172.16.10.192 | 172.16.10.193 | 172.16.10.206 | 172.16.10.207 |
| 192.168.100.14/29 | 192.168.100.8 | 192.168.100.9 | 192.168.100.14 | 192.168.100.15 |

### ✅ Answer Type 3

| Required Hosts | Smallest Subnet | Usable Hosts |
|---:|---|---:|
| 50 | /26 | 62 |
| 100 | /25 | 126 |
| 25 | /27 | 30 |
| 12 | /28 | 14 |
| 2 | /30 | 2 |

### 🧩 Answer Type 4

Four equal subnets from `192.168.30.0/24` are `/26` networks.

| Network | First Usable | Last Usable | Broadcast |
|---|---|---|---|
| 192.168.30.0/26 | 192.168.30.1 | 192.168.30.62 | 192.168.30.63 |
| 192.168.30.64/26 | 192.168.30.65 | 192.168.30.126 | 192.168.30.127 |
| 192.168.30.128/26 | 192.168.30.129 | 192.168.30.190 | 192.168.30.191 |
| 192.168.30.192/26 | 192.168.30.193 | 192.168.30.254 | 192.168.30.255 |

### 🛠️ Answer Type 5

Given:

```text
IP address: 192.168.40.130
Subnet mask: 255.255.255.192
```

The mask is `/26`, so the block size is:

```text
256 - 192 = 64
```

Subnets:

```text
192.168.40.0
192.168.40.64
192.168.40.128
192.168.40.192
```

Answer:

| Item | Value |
|---|---|
| Network address | 192.168.40.128 |
| Usable range | 192.168.40.129 - 192.168.40.190 |
| Broadcast address | 192.168.40.191 |
| Default gateway | 192.168.40.1 |
| Is gateway in same subnet? | No |
| Likely problem | The default gateway is outside the device's subnet |

### 🔢 Answer Type 6

#### 1. 10.20.30.40/16

```text
Mask: 11111111 11111111 00000000 00000000
      NNNNNNNN NNNNNNNN HHHHHHHH HHHHHHHH
```

| Item | Value |
|---|---|
| Subnet mask | 255.255.0.0 |
| Network address | 10.20.0.0 |
| Broadcast address | 10.20.255.255 |
| First usable IP | 10.20.0.1 |
| Last usable IP | 10.20.255.254 |

#### 2. 172.16.50.100/20

```text
Mask: 11111111 11111111 11110000 00000000
      NNNNNNNN NNNNNNNN NNNNHHHH HHHHHHHH
```

| Item | Value |
|---|---|
| Subnet mask | 255.255.240.0 |
| Network address | 172.16.48.0 |
| Broadcast address | 172.16.63.255 |
| First usable IP | 172.16.48.1 |
| Last usable IP | 172.16.63.254 |

#### 3. 192.168.5.130/25

```text
Mask: 11111111 11111111 11111111 10000000
      NNNNNNNN NNNNNNNN NNNNNNNN NHHHHHHH
```

| Item | Value |
|---|---|
| Subnet mask | 255.255.255.128 |
| Network address | 192.168.5.128 |
| Broadcast address | 192.168.5.255 |
| First usable IP | 192.168.5.129 |
| Last usable IP | 192.168.5.254 |

#### 4. 192.168.10.75/27

```text
Mask: 11111111 11111111 11111111 11100000
      NNNNNNNN NNNNNNNN NNNNNNNN NNNHHHHH
```

| Item | Value |
|---|---|
| Subnet mask | 255.255.255.224 |
| Network address | 192.168.10.64 |
| Broadcast address | 192.168.10.95 |
| First usable IP | 192.168.10.65 |
| Last usable IP | 192.168.10.94 |

#### 5. 10.1.2.3/8

```text
Mask: 11111111 00000000 00000000 00000000
      NNNNNNNN HHHHHHHH HHHHHHHH HHHHHHHH
```

| Item | Value |
|---|---|
| Subnet mask | 255.0.0.0 |
| Network address | 10.0.0.0 |
| Broadcast address | 10.255.255.255 |
| First usable IP | 10.0.0.1 |
| Last usable IP | 10.255.255.254 |

## 🚀 Suggested Improvements

- Add a quick subnet mask memorization chart for `/24` through `/30`.
- Have students solve the questions first by hand, then verify with an online subnet calculator.
- Add a short timed quiz at the end with 5 subnetting questions.
- Include one real-world design problem, such as segmenting Admin, Staff, VoIP, Cameras, and Guest Wi-Fi.
- Connect this lesson to the CLI lesson by having students check their own IP, subnet mask, default gateway, and determine their real network range.

## 🌐 Online CIDR Calculators

Use these to verify your hand calculations after you solve the problems manually:

| Tool | Link | Good For |
|---|---|---|
| SolarWinds Advanced Subnet Calculator | https://www.solarwinds.com/free-tools/advanced-subnet-calculator | Subnet ranges, address blocks, and subnet planning |
| SubnetCalculator.dev | https://www.subnetcalculator.dev/ | Quick CIDR, subnet mask, and IP range checks |
| SwissKnifeCalculator Subnet & CIDR Calculator | https://www.swissknifecalculator.com/tools/ip-subnet-cidr | IPv4/IPv6, wildcard masks, VLSM, and export options |
