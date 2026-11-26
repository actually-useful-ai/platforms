// Excerpt of lukeslp/mandaza android/app/build.gradle.kts at b39341f, the commit
// fdroiddata !55922 builds (gradle: fdroid). Kept: flavors, signing and build types.
// The file has no dependenciesInfo block; its release APK is built unsigned and
// signed with apksigner afterward, so Gradle never writes the dependency block.
plugins {
    id("com.android.application")
    kotlin("android")
}

android {
    namespace = "com.lukesteuber.mandaza"
    compileSdk = 36

    defaultConfig {
        applicationId = "app.mandaza.android"
        versionCode = 10303
        versionName = "$marketingVersion.$androidPatchVersion"
    }

    flavorDimensions += "distribution"
    productFlavors {
        create("direct") {
            dimension = "distribution"
            versionCode = 10318
            versionName = "$marketingVersion.11"
        }
        create("play") {
            dimension = "distribution"
            versionCode = 10317
            versionName = "$marketingVersion.10"
        }
        create("amazon") {
            dimension = "distribution"
            versionCode = 10308
        }
        create("fdroid") {
            dimension = "distribution"
            // 1.3.13 follows F-Droid 1.3.12 (10319) with the same app. It exists so the tag F-Droid
            // reads has no Apple listing text in a root metadata folder (see docs/FDROID.md).
            versionCode = 10320
            versionName = "$marketingVersion.13"
        }
    }

    signingConfigs {
        if (hasReleaseSigning) {
            create("release") {
                storeFile = file(signingValues.getValue("MANDAZA_ANDROID_STORE_FILE")!!)
                storePassword = signingValues.getValue("MANDAZA_ANDROID_STORE_PASSWORD")
                keyAlias = signingValues.getValue("MANDAZA_ANDROID_KEY_ALIAS")
                keyPassword = signingValues.getValue("MANDAZA_ANDROID_KEY_PASSWORD")
            }
        }
    }

    buildTypes {
        debug {
            applicationIdSuffix = ".debug"
            versionNameSuffix = "-debug"
        }
        release {
            // R8 code and resource shrinking for every release flavor (direct, play, amazon, fdroid).
            // Keep rules beyond the libraries' own consumer rules live in proguard-rules.pro.
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            if (hasReleaseSigning) signingConfig = signingConfigs.getByName("release")
        }
    }
}
