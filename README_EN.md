# PhotoMetaClean

[Deutsch](README.md) · **English**

PhotoMetaClean checks photos for known AI metadata, including records saved by Adobe Lightroom. You can see what the file says about how the photo was taken and edited, and remove supported entries from a copy. The free app runs locally on Windows, macOS and Linux without an account or a photo upload. [Download the app](https://github.com/Zimbo88/PhotoMetaClean/releases/latest) · [Startup guide](docs/START.md#english)

A night photograph is still a photograph when AI helped reduce the noise. A client who sees an “AI” label under the picture may reasonably wonder whether the whole scene was generated. I’m sharing PhotoMetaClean to help photographers I know explain that distinction to their clients.

## Prepare a folder for a client

1. Drag your photo folder into the window. **Complete customer folder** is selected by default.
2. Review the options under **Remove from copies** and click **Clean copies**.
3. Choose **Show copies**. The **Patch** folder contains the checked copies alongside all unchanged files in their original folder structure. The **Result** column tells you what was removed or why a picture was kept as it was.

Your originals stay in place. Private reports go in a separate folder called **Patch-Protokolle**. Choose **Only changed files** for a smaller test export. To remove supported Lightroom settings or recorded retouching steps, select **Also remove editing history from copies**. The edits you can see remain part of the picture. [Supported editing records](docs/editing-history.md#english)

## Which records can the app remove?

Examples include AI source labels in JPEGs and generator settings in PNGs. An entry may describe how a whole image was created or how one part of it was edited. Your original capture and your knowledge of the edit can help you decide whether a particular label is accurate. [How the app recognizes records](docs/marker.md#how-does-photometaclean-recognize-ai-indicators)

HDR support depends on the file layout. For supported JPEGs, the app checks the compressed image data, decoded pixels and colour profile. For supported HDR JPEGs it also checks the embedded brightness image, called a **gain map**. An unfamiliar layout, extra video data or an inconclusive check can leave an entry in place. In complete-folder mode the app then delivers a byte-for-byte copy. RAW files can be inspected and copied unchanged. [JPEG and HDR details](docs/jpeg-export.md#jpeg-copies-with-and-without-hdr)

## What about signed provenance?

On supported files the JPEG export can also remove a signed record from the copy. That copy then loses its embedded proof of provenance. To keep it, turn off **AI records and credentials in JPEGs**. Before sharing a photo, check the applicable rights, disclosure requirements and terms of use. Adobe’s terms for its generative AI features prohibit removing, altering or disabling Content Credentials. [Adobe guidelines, section 6](https://www.adobe.com/legal/licenses-terms/adobe-gen-ai-user-guidelines.html) · [Photography and usage rights](docs/nutzung.md#english)

## If a platform still shows an AI label

PhotoMetaClean recognizes the entries known to this project. Watermarks embedded in the pixels are outside the scope of this check. Platforms disclose only part of how they identify AI use. A label can still appear after a successful file check. Use **Report an AI label** to preview a short technical report, copy it and share it in the project forum. Include the platform and the exact wording of the label. Keep the picture and full private logs on your computer. [Project forum](https://github.com/Zimbo88/PhotoMetaClean/discussions) · [Platform research](research/14_PLATTFORMKENNZEICHNUNG.md)

## Use and contributions

You may use PhotoMetaClean privately and for paid photography work, and you may sell your photographs. You can modify the software and share it free of charge under the project license. Selling the software is prohibited. © 2026 Mathias Zimmermann. [License and warranty](LICENSE) · [Contributing](CONTRIBUTING.md) · [Privacy](PRIVACY.md)
