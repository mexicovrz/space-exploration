from os.path import join
from re import DOTALL, MULTILINE, subn

from pythonforandroid.recipe import CompiledComponentsPythonRecipe
from pythonforandroid.toolchain import current_directory


class PygameCERecipe(CompiledComponentsPythonRecipe):
    """Build pygame-ce against the SDL2 bootstrap instead of pip/meson.

    pip would cross-compile the meson backend, which does not see the
    Android SDL libraries. This recipe writes Setup from the Android template
    the way the upstream pygame recipe does.
    """

    version = "2.5.8"
    url = "https://github.com/pygame-community/pygame-ce/archive/refs/tags/{version}.tar.gz"

    site_packages_name = "pygame"
    name = "pygame-ce"

    depends = [
        "sdl2",
        "sdl2_image",
        "sdl2_mixer",
        "sdl2_ttf",
        "setuptools",
        "jpeg",
        "png",
    ]
    # CompiledComponentsPythonRecipe builds with p4a's isolated hostpython,
    # not the Python used to launch Buildozer. pygame-ce imports Cython from
    # setup.py, so installing Cython only in the GitHub Actions environment is
    # insufficient.
    hostpython_prerequisites = ["setuptools", "Cython>=3.0,<=3.2.9"]
    call_hostpython_via_targetpython = False
    install_in_hostpython = False

    def prebuild_arch(self, arch):
        super().prebuild_arch(arch)
        with current_directory(self.get_build_dir(arch.arch)):
            # pygame-ce uses Meson for normal wheel builds. p4a's
            # CompiledComponentsPythonRecipe later runs ``pip install .``;
            # leaving the upstream backend enabled makes that command start a
            # native Meson build and try to execute an Android sanity-check
            # binary on the Linux build host. Use pygame-ce's setuptools
            # setup.py implementation, which supports the Android Setup file
            # generated below.
            with open("pyproject.toml", encoding="utf-8") as pyproject:
                pyproject_contents = pyproject.read()
            pyproject_contents, replacements = subn(
                r"^\[build-system\]\n.*?(?=^\[)",
                "[build-system]\n"
                'requires = ["setuptools", "Cython>=3.0,<=3.2.9"]\n'
                'build-backend = "setuptools.build_meta"\n\n',
                pyproject_contents,
                count=1,
                flags=MULTILINE | DOTALL,
            )
            if replacements != 1:
                raise ValueError("pygame-ce pyproject.toml has no build-system block")
            with open("pyproject.toml", "w", encoding="utf-8") as pyproject:
                pyproject.write(pyproject_contents)

            setup_template = open(join("buildconfig", "Setup.Android.SDL2.in")).read()

            png = self.get_recipe("png", self.ctx)
            png_lib_dir = join(png.get_build_dir(arch.arch), ".libs")
            png_inc_dir = png.get_build_dir(arch)

            jpeg = self.get_recipe("jpeg", self.ctx)
            jpeg_inc_dir = jpeg_lib_dir = jpeg.get_build_dir(arch.arch)

            sdl_mixer_includes = ""
            sdl2_mixer_recipe = self.get_recipe("sdl2_mixer", self.ctx)
            for include_dir in sdl2_mixer_recipe.get_include_dirs(arch):
                sdl_mixer_includes += f"-I{include_dir} "

            sdl2_image_includes = ""
            sdl2_image_recipe = self.get_recipe("sdl2_image", self.ctx)
            for include_dir in sdl2_image_recipe.get_include_dirs(arch):
                sdl2_image_includes += f"-I{include_dir} "

            setup_file = setup_template.format(
                sdl_includes=(
                    " -I" + join(self.ctx.bootstrap.build_dir, "jni", "SDL", "include")
                    + " -L" + join(self.ctx.bootstrap.build_dir, "libs", str(arch))
                    + " -L" + png_lib_dir
                    + " -L" + jpeg_lib_dir
                    + " -L" + arch.ndk_lib_dir_versioned
                ),
                sdl_ttf_includes="-I" + join(self.ctx.bootstrap.build_dir, "jni", "SDL2_ttf"),
                sdl_image_includes=sdl2_image_includes,
                sdl_mixer_includes=sdl_mixer_includes,
                jpeg_includes="-I" + jpeg_inc_dir,
                png_includes="-I" + png_inc_dir,
                freetype_includes="",
            )
            open("Setup", "w").write(setup_file)

    def get_recipe_env(self, arch):
        env = super().get_recipe_env(arch)
        env["USE_SDL2"] = "1"
        env["PYGAME_CROSS_COMPILE"] = "TRUE"
        env["PYGAME_ANDROID"] = "TRUE"
        return env


recipe = PygameCERecipe()
