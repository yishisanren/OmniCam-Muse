#!/system/bin/sh
MUSE_MODEL='PME110'
MUSE_FIRMWARE='PME110_17.0.0.103(CN01)'
MUSE_CAMERA_SHA256='6ff0a021288529bdd8eb957827322c71b85c50c93b1715f9e34ab77a7c70a0e6'
MUSE_ALGO_SHA256='8e6ce18cefae51089b8318970daea3087fb6434fed42d55810bf7456df8d66e5'
muse_device_matches() {
    [ "$(getprop ro.product.model)" = "$MUSE_MODEL" ] &&
    [ "$(getprop ro.build.display.id)" = "$MUSE_FIRMWARE" ] &&
    [ "$(sha256sum /product/app/OplusCamera/OplusCamera.apk | cut -d " " -f 1)" = "$MUSE_CAMERA_SHA256" ] &&
    [ "$(sha256sum /odm/lib64/libAlgoInterface.so | cut -d " " -f 1)" = "$MUSE_ALGO_SHA256" ]
}
muse_mounts_match() {
    [ "$(sha256sum /odm/etc/camera/config/camera_unit_config | cut -d " " -f 1)" = "20d7d57e8651af9949a92f3e4214996fe84887d20a32bffe44c4d06738ceb5cb" ] || return 1
    [ "$(sha256sum /odm/etc/camera/config/camera_unit_feature_config.protobuf | cut -d " " -f 1)" = "4dfdcc5e40724ac857440bc17da5905fcce42ad4f98da0054f3fa4be5d907e14" ] || return 1
    [ "$(sha256sum /odm/etc/camera/config/oplus_camera_config | cut -d " " -f 1)" = "0c70fcaa0c6e25710abea06d9e103fbdbab3862034cac04a2450112ace8fab4d" ] || return 1
    [ "$(sha256sum /odm/etc/camera/config/oplus_camera_algo_switch_config | cut -d " " -f 1)" = "f4acfc46a339a222481499dd53770dc298d517e7d7792d18465a29481687011d" ] || return 1
    [ "$(sha256sum /odm/etc/camera/config/oplus_camera_aps_config | cut -d " " -f 1)" = "d5bb514648cc426beac92a0864c07bacb0d0a58546ee01a4c31a3e38007e4731" ] || return 1
    [ "$(sha256sum /odm/lib64/libBasicTonePhoto.so | cut -d " " -f 1)" = "3aaa79dc15bde658d718cb5e8b60c566e9221b038b2cc60fbe160dfd1a58fe09" ] || return 1
    [ "$(sha256sum /odm/lib64/libBasicTonePhotoX10.so | cut -d " " -f 1)" = "56ef69910177f1766d2ca922da0c1aa3ef1893ecc9b3892cff986bfc112a95cc" ] || return 1
    [ "$(sha256sum /odm/lib64/libBasicTonePhotoX9.so | cut -d " " -f 1)" = "57941d57cb81bebb5eb52bf5779bdee7e2932ea038efb590cbe1c8837457ebbe" ] || return 1
    [ "$(sha256sum /odm/lib64/libmsnativefilter.so | cut -d " " -f 1)" = "1468143a7fd647170e4083abe9857e61d2a6fe9179e9fad008578c8417d592dd" ] || return 1
    [ "$(sha256sum /odm/lib64/libAlgoInterface.so | cut -d " " -f 1)" = "8e6ce18cefae51089b8318970daea3087fb6434fed42d55810bf7456df8d66e5" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/JG_FILM_CINESTILL_50D.cube.rgb.bin | cut -d " " -f 1)" = "ba7301ddaa56802c4cb738d9c35a04deb9ebc509d0092b7213c6470951f80d64" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/JG_FILM_FUJI_C200.cube.rgb.bin | cut -d " " -f 1)" = "01757284240ca8241c78fd817388bfd5614e06b049fe46ef7d4dbda8a03a92df" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/JG_FILM_HASSELBLAD_BLUE.cube.rgb.bin | cut -d " " -f 1)" = "d704f62dd18eff41270b5b01b836a87839e5ebf9ae3e467e63302a84ad61fc35" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/JG_FILM_KODAK_5203.cube.rgb.bin | cut -d " " -f 1)" = "c5299e58d6da61cd68f2cf769c22dd794f579b3b1c06c2009d4ad9b84449edfd" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/JG_FILM_KODAK_5207.cube.rgb.bin | cut -d " " -f 1)" = "1cc7e66b2c8215f2a1439b3074ee94b304351f9970250f96c2af24d285b06dfd" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/JG_FILM_KODAK_5219.cube.rgb.bin | cut -d " " -f 1)" = "db15f9ec36fbd48c6f06b2ab8e14ce51146b22b2abe34b1296d769e5b6e12c14" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/JG_FILM_KODAK_E200.cube.rgb.bin | cut -d " " -f 1)" = "f99c3fb9f562cb069b850e3a46d81127aa08f7fbf98990c1636a9d6e319e67e0" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/JG_FILM_KODAK_GOLD_200.cube.rgb.bin | cut -d " " -f 1)" = "82ba980898816771401ee6e3fa8b667d3fb90d88f7d357a9adc520b48d732202" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/JG_FILM_KODAK_PORTRA_400.cube.rgb.bin | cut -d " " -f 1)" = "de4b360715c38fb100b90e122961e7ce05ab7520e42dfd1bf01475ced5b62a04" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/JG_FILM_KODAK_ULTRAMAX_400.cube.rgb.bin | cut -d " " -f 1)" = "767c75c1e46eda91cf0be691d3411e3e5a1c5a167639c1b849dcc9666e7652fa" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/JG_FUJI_NOSTALGIC_NEG.cube.rgb.bin | cut -d " " -f 1)" = "785e565881842b2fcf8468d39e79eb2c64a7d1a9f1d8031920209aa0b7a59601" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/JG_RICOH_CINEMA_GREEN.cube.rgb.bin | cut -d " " -f 1)" = "45204ccd71567e9858e11ba2dcebff677d35624a82801a204947f50d9d25921b" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/JG_RICOH_CINEMA_YELLOW.cube.rgb.bin | cut -d " " -f 1)" = "ac14558931ea97c17635745d64bc90f2d9b5fcb343e39dc571978d94b5313fca" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/JG_RICOH_NEGATIVE.cube.rgb.bin | cut -d " " -f 1)" = "6a8f8b5c3ddbc9f1278925e149ff83d3fb2dcc963dc8c4ec1a4739b32ea14e7b" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/JG_RICOH_POSITIVE.cube.rgb.bin | cut -d " " -f 1)" = "f99ccdf2d3cb4ff3f25143beb81080a0da25874f41818d3bf8835d51bc4d0a90" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/JG_RICOH_VIVID.cube.rgb.bin | cut -d " " -f 1)" = "9214a2b24bf140fbcec7b3f547821f67570e3628f5165728f5801df2857cd276" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/LUT65_A01.cube.rgb.bin | cut -d " " -f 1)" = "cc30095af94a6bf69897d1df4b7e1435b94e193afb62dc00a8ce9285e5db8dab" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/LUT65_A02.cube.rgb.bin | cut -d " " -f 1)" = "7a9dfdc7d75a6451dd21b65deac721510c42196a94b29c5b0377f79aeddd6add" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/LUT65_A03.cube.rgb.bin | cut -d " " -f 1)" = "4e568b3914c1d1488499503f3f9fe0c8d56bd83c720258f20f9d3913e9208794" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/LUT65_A04.cube.rgb.bin | cut -d " " -f 1)" = "88fadf1a3e4014ee42e4936cdda79e8f9de6ffd78125010f0a02f64a6dd8a4f0" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/LUT65_A05.cube.rgb.bin | cut -d " " -f 1)" = "2fd8dc783680de7dfdacf8e531a21a528696701b603588697cf217becd015f01" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/LUT65_A06.cube.rgb.bin | cut -d " " -f 1)" = "69fdef52f8a47abf2a940db77e101125995535ea546f6449a9ed4af40c5d491b" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/LUT65_A07.cube.rgb.bin | cut -d " " -f 1)" = "8e8621cb18e6354dfb0d9b74630efaf0fd58db2574a2ac5bd6cfdce8cae4016d" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/LUT65_A08.cube.rgb.bin | cut -d " " -f 1)" = "4f4a07634bb26b7f92ca3f9342b70e8ac5ed6d35fd605fc618451cb0428fa2a8" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/LUT65_A09.cube.rgb.bin | cut -d " " -f 1)" = "1c7eedfcce2661987e6cbe65e66fa12c6984bca7bdacf59b1ea1abe9155f22fa" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/LUT65_A10.cube.rgb.bin | cut -d " " -f 1)" = "08ccc86575abf82c1ddb689a55fa7118ffb0e8e45eb2724c03b97a1459c9a504" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/LeicaM9.cube.rgb.bin | cut -d " " -f 1)" = "c65e2dcd9beb0cebd8207217c35c59677ca5bb4a938d73608213c62ed630e41b" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/Polaroid_flash.bin | cut -d " " -f 1)" = "c61d79b6b2b958213110213937d20308587fd5b15eb4a87c5a7c11869620296b" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/Polaroid_normal.bin | cut -d " " -f 1)" = "71ca63b261f8d03c65a53553fea506e1d7509f67d51fc924e3694d4dc960c422" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/ccd_flash_cold.bin | cut -d " " -f 1)" = "f6145b9e73b74912053e8517f82490dd6c64499309d510cb639f822de256612b" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/ccd_flash_warm.bin | cut -d " " -f 1)" = "f6145b9e73b74912053e8517f82490dd6c64499309d510cb639f822de256612b" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/ccd_normal_cold.bin | cut -d " " -f 1)" = "37dd88404dddd50155f786609bb6098e15e51a4e85b51b82214ce4ebd15eea9a" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/ccd_normal_warm.bin | cut -d " " -f 1)" = "37dd88404dddd50155f786609bb6098e15e51a4e85b51b82214ce4ebd15eea9a" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/ccd_promist_neutral.bin | cut -d " " -f 1)" = "49c93df7709a0f5ab75665ab99a97b421d75d522f19f2ab3ba0354ea79194fcc" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/glow_sdr_gen_0_1.bin | cut -d " " -f 1)" = "6ef64a18fc49d9e4a894e221a49fee7a7464ca4cd3fbbbcfda0fe5850315c3b1" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/glow_sdr_gen_0_1_flash.bin | cut -d " " -f 1)" = "3fd96030c47d3e2ac681571c6f751e5b99e671d27ec94076bc84982b538a59a6" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/glow_sdr_gen_0_1_normal.bin | cut -d " " -f 1)" = "1f1829ac1cc669f94f5697d5e8614077d1171a0a6f6ebef87a40e8fadc9bc3b4" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/hu_po.bin | cut -d " " -f 1)" = "48469124e104227ab5070688b7cdb9f51e324f49de97b7ec6f44659d19e4ec99" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/polaroid-layer1.rgba | cut -d " " -f 1)" = "de0dc4d0589a160586956c38301ac5ab0a162e13cb84d6fca05fe37ef9aba654" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/polaroid-layer2.rgba | cut -d " " -f 1)" = "8fa3e653c68415fb7532cde70f1d1424443e03febc4dc3bbfd5c8a518e05ddd2" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/polaroid_sdr.mslut | cut -d " " -f 1)" = "6668659a3c891baa3f801904f533ecb9f1de341d3c4fc61de8be47d553a63382" ] || return 1
    [ "$(sha256sum /odm/etc/camera/meishe_lut/qing_tou.bin | cut -d " " -f 1)" = "d7c0eef985d67ec8b635ef72d9bceb8a1f4bfb6abc7a3d4de9f6b073e08f8aa1" ] || return 1
    return 0
}
