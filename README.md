# publically hosted at tais.nunobraga.com

# 🎧 SpinLab – Music Marketplace Platform

**Tech Stack:** Python · Flask · SQLAlchemy · PostgreSQL · Jinja2 · Bootstrap · HTML/CSS · Flask-WTF · Flask-Login

---

## 📌 Overview

**SpinLab** is a full-stack web application designed to simulate a marketplace for buying and selling music-related items such as vinyl records, CDs, cassettes, MP3s, and more.

Built with Flask, it includes a wide range of features for both regular users and administrators, providing secure authentication, ad management, messaging, moderation tools, and a responsive interface.

---

## 🎯 Goals

- Facilitate music-related item 'trading' between users.
- Enable intuitive browsing and filters.
- Provide private messaging and commenting on listings.
- Allow full admin control over users, listings, and categories.

---

## 🔐 User Features

- **Authentication**
  - User registration, login, logout (`Flask-Login`)
  - CSRF protection and secure password hashing

- **Profile Management**
  - Update name, email, password, and profile picture
  - Delete account (cascading deletion of related data)

- **Listings (Ads)**
  - Create ads with multiple images (max 5), price in €, dimensions auto-converted to cm
  - Tag system, format selection, release year, condition
  - Edit or soft-delete ads; mark as “sold”

- **Favorites**
  - Add/remove listings to/from favorites

- **Messaging System**
  - Private chat with read/unread status
  - Inline replies and full message history

- **Comments**
  - Post and delete comments on listings

---

## 🔍 Public (Unauthenticated) Access

- View listing catalog (20 per page)
- Search and filter by:
  - Price (asc/desc)
  - Category
  - Artist/Band
  - Year
  - Format
  - Tags
- Clicking on a listing redirects to login or registration

---

## 🛠️ Admin Panel

- **Dashboard with statistics**
  - Total users, ads, categories

- **User Management**
  - Search by ID
  - Promote/demote roles (admin/user)
  - Edit or permanently delete users

- **Ad Management**
  - View deleted/active/sold ads
  - Restore or permanently delete
  - Cleanup ads deleted over 7 days ago

- **Category Management**
  - Add or deactivate categories

- **Message Moderation**
  - View private conversation between any two users

---

## 🧰 Technology Stack

| Layer         | Technologies                              |
|---------------|--------------------------------------------|
| Backend       | Python, Flask, SQLAlchemy                  |
| Database      | PostgreSQL (or SQLite for local dev)       |
| Authentication| Flask-Login, Flask-WTF, Werkzeug           |
| Frontend      | Jinja2, HTML5, CSS3, Bootstrap 5           |
| Forms         | Flask-WTF, WTForms                         |
| Image Uploads | Secure upload with validation              |
| Features      | Pagination, Filters, Tags, Flash messages  |

---



