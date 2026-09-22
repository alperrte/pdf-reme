<p align="center">
  <a href="README.md">🇹🇷 Türkçe</a> &nbsp;|&nbsp; 🇬🇧 English
</p>

<p align="center">
  <img src="src/pdf_reme/resources/images/git_images/banner.png" alt="PDF-REME" width="100%" />
</p>

<p align="center">
  A locally operated desktop tool that brings PDF viewing, page editing, merging, splitting, conversion,<br />
  compression, and security into one modern application.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Version-v1.0.0-2563EB" alt="Version 1.0.0" />
  <img src="https://img.shields.io/badge/Platform-Windows%20x64-0078D4?logo=windows11&amp;logoColor=white" alt="Windows x64" />
  <img src="https://img.shields.io/badge/Document%20Processing-Local-059669" alt="Local document processing" />
  <img src="https://img.shields.io/badge/Python-3776AB?logo=python&amp;logoColor=white" alt="Python" />
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache--2.0-D22128" alt="Apache License 2.0" /></a>
</p>

## 📥 Download

PDF-REME is published for Windows in two package formats on [GitHub Releases](https://github.com/alperrte/pdf-reme/releases).

| Package | Best for | How to use it |
| --- | --- | --- |
| **Windows Setup** — `PDF-REME-vX.X.X-Setup.exe` | Users who prefer a standard Windows installation | Run the setup wizard, then use PDF-REME like a regular installed app through the Start menu or the optional desktop shortcut. |
| **Portable** — `PDF-REME-vX.X.X-Portable.zip` | Users who do not want to install the app | Download the ZIP, extract it to a folder, and run `PDF-REME.exe`. |

<p align="center">
  <a href="https://github.com/alperrte/pdf-reme/releases"><strong>Open GitHub Releases →</strong></a>
</p>

The Setup and Portable packages provide the same application features in each release. The Portable package keeps settings and application data in the Windows user documents area; only the program files are portable.

## What is PDF-REME?

PDF-REME is an open-source Windows application that brings everyday PDF and document tasks into a single PySide6 desktop interface. Documents are not uploaded to a web service for processing: viewing, editing, conversion, compression, and security operations run on the user’s own computer.

Its local library provides one place to manage imported and generated documents, favorites, recent files, and the trash. Editing in V1 is page-based; direct editing of text and objects inside a PDF is planned for a future release.

## ✨ V1 features

### PDF tools

- View PDF documents
- Merge multiple PDFs while preserving their selected order
- Split a PDF by page selection, custom groups, or number of parts
- Reorder, swap, delete, rotate, and duplicate pages
- Insert pages from another PDF or add a new blank page
- Export selected pages as a new PDF
- Undo and redo page-editing operations

### Conversion

- Convert JPG, JPEG, and PNG images to PDF
- Export all or selected PDF pages as JPG images
- Convert DOC and DOCX documents to PDF
- Convert PPT and PPTX presentations to PDF
- Convert XLS and XLSX workbooks to PDF

Office → PDF conversion runs locally through the LibreOffice Runtime included with the distribution packages.

### Compression and security

- Light, balanced, and strong PDF compression profiles
- Protect a PDF with a user password
- Create an unlocked copy of a protected PDF when the password is known
- AES-256-based PDF encryption

### Document management

- Local library for imported and generated documents
- Favorites and recent files
- Move to trash, restore, and permanently delete
- Generate new outputs without modifying source files

### User experience

- Turkish and English interface
- Light and dark themes
- Modern desktop interface with quick access to common tasks
- Offline use for core document operations

## 🖥️ Product screenshots

<table>
  <tr>
    <td width="50%" valign="top">
      <img src="src/pdf_reme/resources/images/app_images/arayuz.png" alt="PDF-REME dashboard" width="100%" />
      <br /><strong>Dashboard</strong> — Quick access to common tools and recent documents.
    </td>
    <td width="50%" valign="top">
      <img src="src/pdf_reme/resources/images/app_images/kutuphane.png" alt="PDF-REME library" width="100%" />
      <br /><strong>Library</strong> — Manage imported and generated documents in one place.
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <img src="src/pdf_reme/resources/images/app_images/edit.png" alt="PDF-REME page editor" width="100%" />
      <br /><strong>Edit PDF</strong> — Reorder, delete, rotate, duplicate, and insert pages.
    </td>
    <td width="50%" valign="top">
      <img src="src/pdf_reme/resources/images/app_images/convert.png" alt="PDF-REME conversion screen" width="100%" />
      <br /><strong>Convert</strong> — Local workflows for images and Office documents.
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <img src="src/pdf_reme/resources/images/app_images/merge.png" alt="PDF-REME merge screen" width="100%" />
      <br /><strong>Merge PDFs</strong> — Combine multiple files into one PDF in the chosen order.
    </td>
    <td width="50%" valign="top">
      <img src="src/pdf_reme/resources/images/app_images/split.png" alt="PDF-REME split screen" width="100%" />
      <br /><strong>Split PDF</strong> — Separate pages or sections into individual PDF files.
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <img src="src/pdf_reme/resources/images/app_images/compress.png" alt="PDF-REME compression screen" width="100%" />
      <br /><strong>Compress PDF</strong> — Choose from three optimization profiles.
    </td>
    <td width="50%" valign="top">
      <img src="src/pdf_reme/resources/images/app_images/encrypt.png" alt="PDF-REME encryption screen" width="100%" />
      <br /><strong>Encrypt PDF</strong> — Protect documents with a password and AES-256 encryption.
    </td>
  </tr>
</table>

## 📁 Supported formats

| Operation | Formats |
| --- | --- |
| Viewing and PDF tools | PDF |
| Image → PDF | JPG, JPEG, PNG → PDF |
| PDF → Image | PDF → JPG |
| Word → PDF | DOC, DOCX → PDF |
| PowerPoint → PDF | PPT, PPTX → PDF |
| Excel → PDF | XLS, XLSX → PDF |

## 🔒 Local processing

Document viewing and processing workflows run on the local machine; files are not sent to a remote service for conversion or editing. The application may use a network connection only to check GitHub releases when requested by the user or enabled in settings.

## 🧰 Technology stack

<p align="center">
  <img src="src/pdf_reme/resources/images/git_images/tech-stack.png" alt="PDF-REME technology stack" width="100%" />
</p>

## 🗺️ Roadmap

<p align="center">
  <img src="src/pdf_reme/resources/images/git_images/yol-haritasi.png" alt="PDF-REME roadmap" width="100%" />
</p>

The development plan continues with advanced PDF tools and optimization in V1.1, content-level editing and PDF → Office conversion in V2, translation and digital signatures in V3, and local AI features in V4. These capabilities are not part of V1.

## 💻 System requirements

- 64-bit Windows
- Windows Setup or Portable distribution package
- No separate LibreOffice installation is required for Office → PDF conversion; the necessary Runtime is included

## 📄 License

PDF-REME is licensed under the [Apache License 2.0](LICENSE).

## 👨‍💻 Developer

**PDF-REME**<br />
Developed by [Alper Temiz](https://github.com/alperrte).
