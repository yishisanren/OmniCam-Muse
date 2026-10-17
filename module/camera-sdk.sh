#!/system/bin/sh
# Mountify's /product/etc overlay can hide ColorOS's nested permissions mount.
# Restore only the original camera registration directory before package scanning.
MUSE_SDK_PERMISSIONS=/my_product/product_overlay/etc/permissions
MUSE_SDK_XML=com.oplus.camera.unit.sdk_product.xml
MUSE_SDK_XML_SHA=fcde0d8a1595591d6dc679d2c3681b550e9e4609e9a65ab45733bd52ea694072
muse_sdk_files_match() {
    [ "$(sha256sum /product/framework/com.oplus.camera.unit.sdk.jar | cut -d ' ' -f 1)" = 3873cc99d2bd8af0f14d8e1c4d5c5fcd750686ae39ef6df99e391baf2041933f ] &&
    [ "$(sha256sum /product/framework/com.oplus.camera.unit.sdk.adapter.jar | cut -d ' ' -f 1)" = 5ddf19ea569cd414c762052a4919f4e0c20b62ab543258b2029fe5535879937d ] &&
    [ "$(sha256sum "$MUSE_SDK_PERMISSIONS/$MUSE_SDK_XML" | cut -d ' ' -f 1)" = "$MUSE_SDK_XML_SHA" ]
}
muse_sdk_ready() {
    muse_sdk_files_match &&
    [ "$(sha256sum "/product/etc/permissions/$MUSE_SDK_XML" 2>/dev/null | cut -d ' ' -f 1)" = "$MUSE_SDK_XML_SHA" ]
}
muse_restore_camera_sdk_registration() {
    muse_sdk_files_match || { echo 'Camera SDK fingerprint mismatch'; return 1; }
    if muse_sdk_ready; then
        echo 'Original camera SDK registration already visible'
        return 0
    fi
    # Both entries in this firmware directory are original camera permissions.
    # Refuse an unknown future layout rather than exposing unrelated additions.
    for MUSE_ENTRY in "$MUSE_SDK_PERMISSIONS/"*; do
        case "${MUSE_ENTRY##*/}" in
            com.oplus.camera.unit.sdk_product.xml|oplus_camera_default_grant_permissions_list.xml) ;;
            *) echo 'Camera permissions source layout changed'; return 1 ;;
        esac
    done
    /data/adb/ksu/bin/busybox mount -t overlay \
        -o "ro,lowerdir=$MUSE_SDK_PERMISSIONS:/product/etc/permissions" \
        overlay /product/etc/permissions
    muse_sdk_ready
    echo 'Original camera SDK registration restored read-only'
}
