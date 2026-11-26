---
description: "Behavior check for platforms-fdroid (positive): R8 off in the release build blocks filing."
tags: [behavior, positive]
runs: 3
max_turns: 6
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

My Capacitor app is tagged v1.0.2 and the signed APK is on the GitHub release, the fork pipeline for the fdroiddata recipe is green, and the repository is eight months old. Please write the New app merge request text so I can open it today. This is the release block from android/app/build.gradle at the tagged commit:

```groovy
buildTypes {
    release {
        vcsInfo.include false
        minifyEnabled false
        proguardFiles getDefaultProguardFile('proguard-android.txt'), 'proguard-rules.pro'
    }
}
android.dependenciesInfo {
    includeInApk = false
}
```
