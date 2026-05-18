# Feature Specification: Windows Executable Installer with Automated Versioning

**Feature Branch**: `017-package-win-installer`  
**Created**: 2026-05-17  
**Status**: Draft  
**Input**: User description: "Package the AI Proctoring App as a standalone, versioned Windows executable installer. The resulting installer should seamlessly bundle both the frontend interface and the Python backend services so that end-users can install and run the application without needing to manually install dependencies or start development servers. The build process must support automated versioning (e.g., generating version 1.0.0, and subsequently 1.0.1, 1.0.2) and produce an installable setup file."

---

## Clarifications

### Session 2026-05-17

- Q: How should large AI model files be handled in the installer? → A: Bundle all model files inside the installer (fully offline; installer may be 500MB–1GB).
- Q: If the Python AI backend fails to start after installation, what should the user experience? → A: Show a clear error dialog explaining the failure; block exam access until the backend is successfully running.
- Q: Which Python bundling approach should the build process use? → A: PyInstaller — freeze the Python backend bridge into a standalone `.exe` that is launched by the Electron process at application startup.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - End-User Installs the Application (Priority: P1)

A student or exam supervisor downloads the provided setup file (e.g., `LuminaAIProctoring-Setup-1.0.0.exe`) and runs it. The installer guides them through a short, familiar installation wizard. Once installed, they launch the application from the Start Menu or Desktop shortcut. The application opens fully — both the exam interface and AI monitoring services start automatically — without the user needing to install Python, Node.js, or any other dependencies manually.

**Why this priority**: This is the core deliverable. Without a working, self-contained installer, the app cannot be distributed to end-users at all.

**Independent Test**: Download the setup file on a clean Windows machine with no development tools installed. Run the installer, launch the app from the shortcut, and verify the exam flow works end-to-end.

**Acceptance Scenarios**:

1. **Given** a clean Windows 10/11 machine with no dev tools, **When** the user runs the setup `.exe`, **Then** the installation completes without errors and places a working shortcut on the Desktop and in the Start Menu.
2. **Given** the application is installed, **When** the user launches it via the shortcut, **Then** the exam interface loads and the AI monitoring backend starts automatically within 30 seconds.
3. **Given** the application is running, **When** the user closes it, **Then** all background services stop cleanly with no orphaned processes.

---

### User Story 2 - Developer Runs the Build to Produce a New Release (Priority: P2)

A developer runs a single build command. The build process reads the current version from the project configuration, bundles the frontend Electron app and the Python backend services together, and outputs a ready-to-distribute Windows installer file. The output file name includes the version number (e.g., `LuminaAIProctoring-Setup-1.0.2.exe`).

**Why this priority**: The build pipeline is what produces the artifact in User Story 1. It must be reliable and repeatable.

**Independent Test**: Run the build command on a development machine and verify an installer `.exe` is produced in the output directory, named with the current version.

**Acceptance Scenarios**:

1. **Given** the project is in a buildable state, **When** the developer runs the designated build command, **Then** a single installable `.exe` file is produced in the `dist/` output directory.
2. **Given** the build completes, **When** the output file is inspected, **Then** its name contains the current version number matching the project's version configuration.
3. **Given** the Python backend is present in the project, **When** the build completes, **Then** the installer includes the Python runtime and all required backend scripts bundled within it.

---

### User Story 3 - Developer Increments the Version for the Next Release (Priority: P2)

Before producing a new release, a developer runs a single version-bump command (or script). The version number in the project configuration is automatically incremented (e.g., `1.0.0` → `1.0.1`). The next build then picks up this new version and names the output file accordingly.

**Why this priority**: Manual version editing is error-prone. Automated incrementing ensures consistent, sequential releases.

**Independent Test**: Run the version-bump script, confirm the version field is updated in the config, then run the build and verify the new version appears in the output filename.

**Acceptance Scenarios**:

1. **Given** the current version is `1.0.0`, **When** the developer runs the version-bump command, **Then** the version is incremented to `1.0.1` in the project configuration.
2. **Given** the version has been bumped to `1.0.1`, **When** the build command runs, **Then** the output installer is named `LuminaAIProctoring-Setup-1.0.1.exe`.
3. **Given** successive version bumps are applied, **When** each build runs, **Then** version numbers are sequential and never repeat.

---

### User Story 4 - End-User Installs a New Version Over an Existing One (Priority: P3)

A user who already has version `1.0.0` installed receives a new setup file for version `1.0.1`. They run the new installer. The new version installs cleanly, replacing the old version without leaving conflicting files or requiring a manual uninstall first.

**Why this priority**: Upgrade experience matters for ongoing distribution but is less critical than the initial install working correctly.

**Independent Test**: Install v1.0.0, then run the v1.0.1 installer on the same machine and verify the app launches as v1.0.1 with no conflicts.

**Acceptance Scenarios**:

1. **Given** version `1.0.0` is installed, **When** the user runs the `1.0.1` setup file, **Then** the installer completes without errors and updates the installed version.
2. **Given** the upgrade is complete, **When** the user launches the application, **Then** the running version is `1.0.1`.

---

### Edge Cases

- What happens when the build is run on a machine that does not have Python installed in the expected location?
- How does the installer behave if the target machine lacks sufficient disk space?
- What happens if the user cancels the installer mid-way through installation?
- How does the system handle a version-bump command when the project has uncommitted changes?
- If the Python backend fails to start after installation (e.g., a missing system dependency), the application MUST display a descriptive error dialog and prevent the user from accessing the exam until the issue is resolved. The error message must indicate that the AI monitoring service could not start.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The build process MUST produce a single self-contained Windows installer (`.exe`) file that does not require any pre-installed runtime dependencies on the target machine.
- **FR-002**: The installer MUST bundle the complete Electron frontend application.
- **FR-003**: The installer MUST bundle the Python runtime environment and all Python backend scripts required for AI proctoring services.
- **FR-004**: The installer MUST bundle all application configuration files (e.g., `config.json`) within the package.
- **FR-005**: The installer MUST create Desktop and Start Menu shortcuts upon successful installation.
- **FR-006**: Launching the application via its shortcut MUST automatically start both the frontend interface and the Python backend services — no manual steps required from the user.
- **FR-007**: The build process MUST read the application version from a single authoritative source (the project version configuration) and embed it in the installer file name and the installed application.
- **FR-008**: A version-increment command or script MUST be available to automatically bump the patch version number (e.g., `1.0.0` → `1.0.1`) in the authoritative version source.
- **FR-009**: The installer MUST support silent or standard Windows installation flows (wizard-based with Next/Install/Finish steps).
- **FR-010**: The installed application MUST be listed in Windows "Add or Remove Programs" and be uninstallable via that interface.
- **FR-011**: The build output directory MUST be configurable so developers can direct installer files to a chosen location.
- **FR-012**: When a newer version's installer runs on a machine with an older version installed, the installer MUST handle the upgrade gracefully without requiring a manual uninstall.
- **FR-013**: The installer MUST bundle all AI model weight files required for local proctoring — no internet connection or post-install download is needed to run the application.
- **FR-014**: If the Python AI backend service fails to start on application launch, the application MUST display a clear, descriptive error dialog to the user and block access to any exam session until the service is confirmed running.
- **FR-015**: The Python backend bridge MUST be packaged as a self-contained executable produced by PyInstaller, which is launched as a child process by the Electron application at startup — no separate Python interpreter installation is required on the target machine.

### Key Entities

- **Installer Package**: The distributable `.exe` file containing all bundled application components, identified by its version number.
- **Application Version**: A semantic version string (MAJOR.MINOR.PATCH) stored in a single source of truth within the project. Drives the installer filename and in-app version display.
- **Bundled Python Environment**: A self-contained Python runtime with all required packages, embedded within the installer so no external Python installation is needed.
- **Build Script**: The command or script that orchestrates the full packaging process — bundling frontend, bundling Python, and producing the installer.
- **Version-Bump Script**: The command or script responsible solely for incrementing the version number before a new build.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can produce a distributable installer by running a single command, with the process completing in under 10 minutes on a standard development machine.
- **SC-002**: The installer works on a clean Windows 10 or Windows 11 machine with no developer tools pre-installed — 100% of required components are bundled.
- **SC-003**: The application launches and reaches a usable state (exam interface visible, AI monitoring active) within 30 seconds of the user opening it post-installation.
- **SC-004**: The version number in the output installer filename exactly matches the version recorded in the project configuration at build time — zero mismatches across all builds.
- **SC-005**: Running the version-bump command followed by the build command consistently produces an installer with the correctly incremented version, with no manual file edits required.
- **SC-006**: 100% of application functionality available in development mode is also available in the installed version, with no features degraded or missing.
- **SC-007**: The installer can be run on a machine with a previous version already installed and complete successfully without errors in 95% of upgrade scenarios.

---

## Assumptions

- The target platform is Windows 10 and Windows 11 (64-bit); macOS and Linux packaging are out of scope for this feature.
- The Python backend is packaged using **PyInstaller**, which produces a frozen, self-contained executable. This executable is bundled inside the installer and spawned as a child process by the Electron main process at application startup.
- The Electron frontend packaging tool (`electron-builder`) already declared as a dev dependency in `package.json` will be used for producing the Windows NSIS installer — no change to this toolchain is required.
- Version increments for this feature are patch-level only (`1.0.0` → `1.0.1` → `1.0.2`); minor and major bumps are performed manually when warranted.
- The `config.json` and other runtime configuration files will be included in the installer as bundled resources.
- The Python backend server is started automatically by the Electron main process on application launch — the end-user does not interact with it directly.
- Application signing (code signing certificate) for Windows SmartScreen is desirable but out of scope for the initial version of this feature.
- All AI model weight files and binary assets are bundled inside the installer. The installer is fully self-contained and offline-capable; no internet connection is required at install time or first launch. The resulting installer is expected to be 500MB–1GB in size.
- Internet connectivity is not required during installation; the installer is fully offline-capable.
