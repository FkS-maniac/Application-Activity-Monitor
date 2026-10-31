# Application-Activity-Monitor
A desktop application for tracking application launches and exits, measuring usage time, and managing a list of monitored applications. Status: Work in progress. This is not a final release. Prebuilt binaries are not available yet, and build instructions will be added later.

About
The project aims to provide application activity monitoring with minimal background resource usage. The planned approach focuses on detecting when processes start and stop, then calculating the duration of each session.

System processes are intended to be excluded based on the user account under which they run.

Planned Features
 1. Detect application launches and exits.
 2. Calculate the duration of each usage session.
 3. Filter out system processes.
 4. Manage a small, configurable allowlist of applications.
 5. Save successfully detected applications to the main monitoring list.
 6. Exclude applications that could not be detected from further detection attempts.
 7. Reset the detected-process list and populate it with newly detected applications.
 8. Limit concurrent background tasks to reduce resource usage.

How It Is Intended to Work
  1. The user defines an allowlist of applications to detect.
  2. The application checks the candidates and filters out system processes.
  3. Successfully detected applications are saved to the main monitoring list.
  4. Candidates that could not be detected are excluded from further attempts.
  5. The monitor records process start and exit events for tracked applications.
  6. Once a process exits, the duration of its session is calculated.

Development Status
The project is under active development, and its behavior is still being refined. The features described above represent the intended functionality and may not yet be fully implemented.

The project structure, interface, and process detection logic may change before the first stable release.

Building and Running
No prebuilt binaries are available at this stage. Compilation, installation, and usage instructions will be published when the project is ready for its first release.

Feedback
Feature suggestions and bug reports are welcome in the repository’s Issues section. When reporting a problem, include the expected behavior, the actual result, and steps to reproduce it.
