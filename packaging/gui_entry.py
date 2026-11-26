from multiprocessing import freeze_support

if __name__ == "__main__":
    freeze_support()
    from photometaclean.gui.app import main

    raise SystemExit(main())
