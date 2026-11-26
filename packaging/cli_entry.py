from multiprocessing import freeze_support

if __name__ == "__main__":
    freeze_support()
    from photometaclean.cli.app import main

    raise SystemExit(main())
