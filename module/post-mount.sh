#!/system/bin/sh
set -eu
MODDIR=${0%/*}
NOMOUNT=/data/adb/modules/nomount/bin/nm
exec >> "$MODDIR/libraries.log" 2>&1
. "$MODDIR/device-profile.sh"
muse_device_matches || exit 0
. "$MODDIR/camera-sdk.sh"
muse_restore_camera_sdk_registration

bind_library() {
    NAME=$1
    SOURCE="$MODDIR/system/odm/lib64/$NAME"
    TARGET="/odm/lib64/$NAME"
    test -f "$SOURCE"
    chown root:root "$SOURCE"
    chmod 0644 "$SOURCE"
    chcon u:object_r:same_process_hal_file:s0 "$SOURCE"
    if [ -x "$NOMOUNT" ] && [ ! -e /data/adb/modules/nomount/disable ]; then
        "$NOMOUNT" rule add "$TARGET" "$SOURCE"
        echo "redirect ok $TARGET"
    fi
}

# skip_mount prevents automatic library overlays before firmware validation.
bind_library libBasicTonePhotoX9.so
bind_library libBasicTonePhotoX10.so
bind_library libBasicTonePhoto.so
bind_library libmsnativefilter.so

if [ -x "$NOMOUNT" ] && [ ! -e /data/adb/modules/nomount/disable ]; then
    "$NOMOUNT" version
elif [ -f /data/adb/modules/mountify/metamount.sh ] && [ ! -e /data/adb/modules/mountify/disable ]; then
    # Keep skip_mount: an OTA must never activate these libraries before validation.
    # The camera namespace retains these overlays but drops ordinary bind mounts.
    # Stage only our own libraries, configuration and resources on ext4.
    if [ -f "$MODDIR/merged/camera-overlay.ready" ] && muse_mounts_match; then
        echo "camera overlays already active"
        exit 0
    fi
    BUSYBOX=/data/adb/ksu/bin/busybox
    test -x "$BUSYBOX"
    LOWER="$MODDIR/merged/camera_lower"
    IMAGE="$MODDIR/merged/camera-overlay.ext4"
    mkdir -p "$LOWER"
    if "$BUSYBOX" mountpoint -q "$LOWER"; then
        echo "Camera overlay source already mounted; refusing to reformat"
        exit 1
    fi
    dd if=/dev/zero of="$IMAGE" bs=1M count=0 seek=128
    /system/bin/mkfs.ext4 -O ^has_journal "$IMAGE"
    "$BUSYBOX" mount -t ext4 -o loop,rw "$IMAGE" "$LOWER"
    mkdir -p "$LOWER/lib64" "$LOWER/config" "$LOWER/meishe_lut" "$LOWER/basictone/setting_Retro"
    cp -a "$MODDIR/system/odm/lib64/". "$LOWER/lib64/"
    for NAME in camera_unit_config camera_unit_feature_config.protobuf oplus_camera_config oplus_camera_algo_switch_config oplus_camera_aps_config; do
        cp "$MODDIR/payload/$NAME" "$LOWER/config/$NAME"
    done
    cp -a "$MODDIR/payload/meishe_lut/". "$LOWER/meishe_lut/"
    cp -a "$MODDIR/payload/x10_basictone/". "$LOWER/basictone/"
    cp -a "$MODDIR/payload/setting_Retro/". "$LOWER/basictone/setting_Retro/"
    chown -R root:root "$LOWER"
    find "$LOWER" -type d -exec chmod 0755 {} \;
    find "$LOWER" -type f -exec chmod 0644 {} \;
    chcon u:object_r:vendor_file:s0 "$LOWER"
    chcon u:object_r:vendor_file:s0 "$LOWER/lib64"
    chcon u:object_r:same_process_hal_file:s0 "$LOWER/lib64/"*.so
    chcon -R u:object_r:vendor_configs_file:s0 "$LOWER/config" "$LOWER/meishe_lut" "$LOWER/basictone"
    "$BUSYBOX" mount -o remount,ro "$LOWER"
    if [ -f /data/adb/modules/mountify/ksud_has_nuke_ext4 ]; then
        /data/adb/ksud kernel nuke-ext4-sysfs "$LOWER" || true
    fi
    "$BUSYBOX" mount -t overlay -o "ro,lowerdir=$LOWER/lib64:/odm/lib64" overlay /odm/lib64
    echo "library overlay ok /odm/lib64"
    for NAME in config meishe_lut basictone; do
        TARGET="/odm/etc/camera/$NAME"
        "$BUSYBOX" mount -t overlay -o "ro,lowerdir=$LOWER/$NAME:$TARGET" overlay "$TARGET"
        echo "camera overlay ok $TARGET"
    done
    muse_mounts_match
    touch "$MODDIR/merged/camera-overlay.ready"
else
    echo "No supported mounting backend available"
    exit 1
fi
