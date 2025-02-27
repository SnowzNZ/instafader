import os
import re
import shutil
from datetime import datetime
from tkinter import colorchooser, messagebox

import customtkinter
from customtkinter import filedialog
from PIL import Image, ImageChops

# Constants
DEFAULT_COLORS = [(255, 192, 0), (0, 202, 0), (18, 124, 255), (242, 24, 57)]

customtkinter.set_appearance_mode("system")
customtkinter.set_default_color_theme("blue")


class Instafader(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.iconbitmap("src/icon.ico")
        self.title("Instafader")
        self.geometry(f"{400}x{500}")

        # Variables
        self.skin_folder: str | None = None
        self.colors: list[tuple[int, int, int]] = []
        self.hitcircle_prefix: str | None = None
        self.selected_color: tuple[int, int, int] | None = None
        self.backup_dir: str | None = None

        # Grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure((0, 1, 2, 3, 4, 5), weight=1)

        # Folder entry
        self.folder_entry = customtkinter.CTkEntry(self, placeholder_text="Skin Folder")
        self.folder_entry.configure(
            state="readonly"
        )  # Set state after button initialization so that the placeholder text is visible
        self.folder_entry.grid(row=0, column=0, padx=(5, 2.5), sticky="ew")

        # Folder select button
        self.folder_select_button = customtkinter.CTkButton(
            self, text="Select Skin Folder", command=self.select_folder
        )
        self.folder_select_button.grid(row=0, column=1, padx=(2.5, 5), sticky="e")

        # Image preview
        placeholder = Image.new("RGBA", (195, 195), (0, 0, 0, 0))
        placeholder_image = customtkinter.CTkImage(
            light_image=placeholder, dark_image=placeholder, size=(195, 195)
        )

        self.image_preview = customtkinter.CTkLabel(
            self, image=placeholder_image, text=""
        )
        self.image_preview.grid(
            row=1, column=0, columnspan=2, padx=5, pady=(20, 10), sticky="n"
        )

        # Color combobox
        self.color_combobox = customtkinter.CTkComboBox(
            self,
            values=[f"{r}, {g}, {b}" for r, g, b in self.colors] + ["Custom Color"],
            command=self.on_color_selected,
            width=200,
            state="readonly",
        )
        self.color_combobox.grid(
            row=2,
            column=0,
            columnspan=2,
            padx=10,
            sticky="n",
        )

        # Instafade button
        self.instafade_button = customtkinter.CTkButton(
            self, text="Instafade!", command=self.instafade
        )
        self.instafade_button.grid(
            row=3,
            column=0,
            padx=(10, 0),
            sticky="ew",
        )

        # Revert button
        self.revert_button = customtkinter.CTkButton(
            self,
            text="Revert",
            command=self.revert_to_backup,
            width=100,
            fg_color="red",
            hover_color="dark red",
        )
        self.revert_button.grid(
            row=3,
            column=1,
            padx=(0, 10),
            sticky="e",
        )

        # Progress bar
        self.progress_bar = customtkinter.CTkProgressBar(self)
        self.progress_bar.grid(
            row=5,
            column=0,
            columnspan=2,
            padx=10,
            pady=(5, 10),
            sticky="ew",
        )
        self.progress_bar.set(0)
        self.progress_bar.grid_remove()

    def select_folder(self) -> None:
        """Select skin folder using file dialog"""
        self.skin_folder = filedialog.askdirectory()
        folder_name = (
            os.path.basename(self.skin_folder) if self.skin_folder else ""
        )  # Display only the folder name, not the full path
        self.folder_entry.configure(
            textvariable=customtkinter.StringVar(self, folder_name)
        )

        self.load_skin_ini()

        if self.colors:
            self.generate_preview(self.colors[0])

    # TODO: extract logic from instafade() and use that when generating previews
    def generate_preview(self, color: tuple[int, int, int]) -> None:
        """Generate preview image using the specified color.

        Args:
            color: RGB color tuple to use for preview
        """
        try:
            # Create temporary backup dir for preview
            preview_backup = os.path.join(self.skin_folder, "preview-temp")
            os.makedirs(preview_backup, exist_ok=True)

            # Load required elements
            hitcircle, hitcircle_hd = self.load_skin_element(
                "hitcircle", preview_backup
            )
            hitcircleoverlay, hitcircleoverlay_hd = self.load_skin_element(
                "hitcircleoverlay", preview_backup
            )
            number, number_hd = self.load_skin_element(
                f"{self.hitcircle_prefix}-1", preview_backup
            )

            # Create colored hitcircle
            solid_color = Image.new(
                mode="RGBA",
                size=(hitcircle.width, hitcircle.height),
                color=color,
            )
            hitcircle = ImageChops.multiply(
                hitcircle.convert("RGBA"), solid_color.convert("RGBA")
            )

            # Resize elements if needed
            hitcircle = self.resize_element(
                hitcircle,
                self.calculate_resize_factor(hitcircle_hd, hitcircleoverlay_hd),
            )
            hitcircleoverlay = self.resize_element(
                hitcircleoverlay,
                self.calculate_resize_factor(hitcircleoverlay_hd, hitcircle_hd),
            )

            # Create composite
            circle = self.create_composite_image(hitcircle, hitcircleoverlay)

            # Add number
            if number.size > circle.size:
                result = Image.new("RGBA", number.size, (255, 255, 255, 0))
                paste_position = (
                    (number.width - circle.width) // 2,
                    (number.height - circle.height) // 2,
                )
                result.paste(circle, paste_position, circle)
                result.paste(number, (0, 0), number)
            else:
                result = circle
                w, h = number.size
                if not number_hd and (hitcircle_hd or hitcircleoverlay_hd):
                    number = number.resize(
                        (w * 2, h * 2), resample=Image.Resampling.LANCZOS
                    )
                    w, h = number.size
                x, y = result.size
                result.paste(number, ((x - w) // 2, (y - h) // 2), number)

            # Convert to PhotoImage and display
            preview_image = customtkinter.CTkImage(
                light_image=result, dark_image=result, size=(195, 195)
            )
            self.image_preview.configure(image=preview_image)
            self.image_preview.image = preview_image  # Keep a reference

            # Cleanup
            shutil.rmtree(preview_backup, ignore_errors=True)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate preview: {e}")

    def on_color_selected(self, choice: str) -> None:
        """Handle color selection from combobox"""
        if choice == "Custom Color":
            if color := colorchooser.askcolor(parent=self)[0]:
                self.selected_color = tuple(map(int, color))
                self.colors.append(self.selected_color)
                self.color_combobox.set(
                    f"{self.selected_color[0]}, {self.selected_color[1]}, {self.selected_color[2]}"
                )
                self.generate_preview(self.selected_color)
        else:
            # Convert string "r, g, b" to tuple
            self.selected_color = tuple(map(int, choice.split(", ")))
            self.generate_preview(self.selected_color)

        self.update_color_options(self.colors)

    def load_skin_ini(self) -> None:
        """Load and parse skin.ini file to extract colors and hitcircle prefix."""
        if not self.skin_folder:
            messagebox.showerror("Error", "No skin folder selected")
            return

        skin_ini = os.path.join(self.skin_folder, "skin.ini")
        if not os.path.exists(skin_ini):
            messagebox.showerror("Error", "skin.ini not found")
            return

        with open(skin_ini, "rb") as f:
            data = f.read().splitlines()

            self.colors = self.get_colors(data)
            self.hitcircle_prefix = self.get_prefix(data)

            self.update_color_options(self.colors)

    # TODO: Cleanup
    def get_colors(self, data: list[bytes]) -> list[tuple[int, int, int]]:
        """Extract combo colors from skin.ini data.

        Args:
            data: List of bytes containing skin.ini file contents

        Returns:
            List of RGB color tuples, or DEFAULT_COLORS if none found
        """
        cols = []
        for line in data:
            if b"Combo" in line and (
                b"//" not in line or line.find(b"//") > line.find(b"Combo")
            ):
                decoded = line.decode("utf-8")[line.find(b"Combo") + 5 :]
                if not decoded[0].isdigit():
                    continue
                decoded = decoded[1:]

                index = 0
                while index < len(decoded):
                    if decoded[index].isdigit():
                        break
                    index += 1
                decoded = decoded[index:]

                col = decoded.strip().split(",")
                col = tuple(int(i.strip()[:3]) for i in col)
                cols.append(col)

        return DEFAULT_COLORS if len(cols) == 0 else cols

    def set_color(self, color: tuple[int, int, int]) -> None:
        """Set single combo color in skin.ini file and remove other combo colors.

        Args:
            color: RGB color tuple to set as Combo1
        """
        try:
            skin_ini_path = os.path.join(self.skin_folder, "skin.ini")

            with open(skin_ini_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            colours_section_found = False
            color_added = False
            new_lines = []

            for line in lines:
                if (
                    not re.match(r"Combo\d+:", line.strip())
                    or "//" in line[: line.find("Combo")]
                ):
                    if "[Colours]" in line:
                        colours_section_found = True
                        new_lines.append(line)
                        new_lines.append(
                            f"Combo1: {color[0]}, {color[1]}, {color[2]}\n"
                        )
                        color_added = True
                    else:
                        new_lines.append(line)

            if not colours_section_found:
                if new_lines and not new_lines[-1].endswith("\n"):
                    new_lines.append("\n")
                new_lines.append("[Colours]\n")
                new_lines.append(f"Combo1: {color[0]}, {color[1]}, {color[2]}\n")
            elif not color_added:
                new_lines.append(f"Combo1: {color[0]}, {color[1]}, {color[2]}\n")

            with open(skin_ini_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to set combo color: {e}")

    def get_prefix(self, data: list[bytes]) -> str:
        """Extract hitcircle prefix from skin.ini data.

        Args:
            data: List of bytes containing skin.ini file contents

        Returns:
            str: Hitcircle prefix, or "default" if not found
        """
        for line in data:
            if b"HitCirclePrefix" in line:
                decoded_line = line.decode("utf-8").strip()
                prefix = decoded_line.split(":", 1)[1].strip()
                return prefix.replace("\\", "/")

        return "default"

    def set_overlap(self, overlap: str) -> None:
        """Set hitcircle overlap in skin.ini file.

        Args:
            overlap: New overlap to set
        """
        try:
            skin_ini_path = os.path.join(self.skin_folder, "skin.ini")

            with open(skin_ini_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            overlap_found = False
            for i, line in enumerate(lines):
                if "HitCircleOverlap" in line and "//" not in line:
                    lines[i] = f"HitCircleOverlap: {overlap}\n"
                    overlap_found = True
                    break

            if not overlap_found:
                fonts_section_index = -1
                for i, line in enumerate(lines):
                    if "[Fonts]" in line:
                        fonts_section_index = i
                        break

                if fonts_section_index == -1:
                    lines.append("\n[Fonts]\n")
                    lines.append(f"HitCircleOverlap: {overlap}\n")
                else:
                    lines.insert(
                        fonts_section_index + 1, f"HitCircleOverlap: {overlap}\n"
                    )

            with open(skin_ini_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to set hitcircle overlap: {e}")

    def update_color_options(self, colors: list[tuple[int, int, int]]) -> None:
        """Update color options in the combo

        Args:
            colors: List of RGB color tuples
        """
        self.color_combobox.configure(
            values=[f"{r}, {g}, {b}" for r, g, b in colors] + ["Custom Color"]
        )

    def create_backup_folder(self) -> None:
        """Create backup directory and return its path"""
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        self.backup_dir = os.path.join(
            self.skin_folder, f"{"instafader-backup"}-{timestamp}"
        )
        os.makedirs(self.backup_dir, exist_ok=True)

    def backup_file(self, file_name: str) -> None:
        """Backup file to backup directory.

        Args:
            file_name: Name of file to backup
        """
        try:
            source_path = os.path.join(self.skin_folder, file_name)
            dest_path = os.path.join(self.backup_dir, file_name)
            shutil.copy2(source_path, dest_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to backup file: {e}")

    def load_skin_element(
        self, basename: str, backup_folder: str
    ) -> tuple[Image.Image, bool]:
        """Load a skin element and backup the original file.

        Args:
            basename: Base name of the file without HD suffix (e.g. "hitcircle")
            backup_folder: Path to backup folder

        Returns:
            tuple: (PIL Image object, bool indicating if HD version)

        Raises:
            FileNotFoundError: If neither HD nor SD version exists
        """
        hd_name = f"{basename}@2x.png"
        sd_name = f"{basename}.png"

        try:
            hd_path = os.path.join(self.skin_folder, hd_name)
            image = Image.open(hd_path)
            shutil.copy2(hd_path, os.path.join(backup_folder, hd_name))
            return image, True
        except FileNotFoundError:
            try:
                sd_path = os.path.join(self.skin_folder, sd_name)
                image = Image.open(sd_path)
                shutil.copy2(sd_path, os.path.join(backup_folder, sd_name))
                return image, False
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"Could not find {basename} in HD or SD version"
                )

    def calculate_resize_factor(self, element_is_hd: bool, other_is_hd: bool) -> float:
        """Calculate the resize factor based on HD status of both elements.

        Args:
            element_is_hd: Whether the current element is HD
            other_is_hd: Whether the other element is HD

        Returns:
            float: Resize factor (2.5 if SD->HD conversion needed, 1.25 for normal scaling)
        """
        return 2.5 if not element_is_hd and other_is_hd else 1.25

    def resize_element(self, image: Image.Image, scale: float) -> Image.Image:
        """Resize an image by a given scale factor.

        Args:
            image: PIL Image to resize
            scale: Scale factor to apply

        Returns:
            Image.Image: Resized image
        """
        new_size = (int(image.width * scale), int(image.height * scale))
        return image.resize(new_size, resample=Image.Resampling.LANCZOS)

    def create_composite_image(
        self, base: Image.Image, overlay: Image.Image
    ) -> Image.Image:
        """Create a composite image by combining two images, centering the smaller one.

        Args:
            base: Base image (hitcircle)
            overlay: Overlay image (hitcircleoverlay)

        Returns:
            Image.Image: Combined image
        """
        base = base.convert("RGBA")
        overlay = overlay.convert("RGBA")

        if base.size == overlay.size:
            return Image.alpha_composite(base, overlay)

        if overlay.size > base.size:
            result = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
            paste_position = (
                (overlay.width - base.width) // 2,
                (overlay.height - base.height) // 2,
            )
            result.paste(base, paste_position, base)
            return Image.alpha_composite(result, overlay)
        else:
            result = Image.new("RGBA", base.size, (0, 0, 0, 0))
            paste_position = (
                (base.width - overlay.width) // 2,
                (base.height - overlay.height) // 2,
            )
            result.paste(base, (0, 0), base)
            temp = Image.new("RGBA", base.size, (0, 0, 0, 0))
            temp.paste(overlay, paste_position, overlay)
            return Image.alpha_composite(result, temp)

    def instafade(self) -> None:
        """Instafade the skin"""
        self.progress_bar.grid()
        self.progress_bar.set(0)
        self.update()

        self.create_backup_folder()
        self.progress_bar.set(0.1)
        self.update()

        self.backup_file("skin.ini")
        self.progress_bar.set(0.2)
        self.update()

        hitcircle, hitcircle_hd = self.load_skin_element("hitcircle", self.backup_dir)
        hitcircleoverlay, hitcircleoverlay_hd = self.load_skin_element(
            "hitcircleoverlay", self.backup_dir
        )
        self.progress_bar.set(0.3)
        self.update()

        solid_color = Image.new(
            mode="RGBA",
            size=(hitcircle.width, hitcircle.height),
            color=self.selected_color,
        )

        hitcircle = ImageChops.multiply(
            hitcircle.convert("RGBA"), solid_color.convert("RGBA")
        )
        self.progress_bar.set(0.4)
        self.update()

        hitcircle = self.resize_element(
            hitcircle, self.calculate_resize_factor(hitcircle_hd, hitcircleoverlay_hd)
        )

        hitcircleoverlay = self.resize_element(
            hitcircleoverlay,
            self.calculate_resize_factor(hitcircleoverlay_hd, hitcircle_hd),
        )
        self.progress_bar.set(0.5)
        self.update()

        circle_hd = hitcircle_hd or hitcircleoverlay_hd

        circle = self.create_composite_image(hitcircle, hitcircleoverlay)
        circle.save(os.path.join(self.skin_folder, "circle.png"))
        self.progress_bar.set(0.6)
        self.update()

        for i in range(1, 10):
            number, number_hd = self.load_skin_element(
                f"{self.hitcircle_prefix}-{i}", self.backup_dir
            )

            circle = Image.open(os.path.join(self.skin_folder, "circle.png"))

            if number.size > circle.size:
                no_number = Image.new("RGBA", number.size, (255, 255, 255, 0))
                paste_position = (
                    (number.width - circle.width) // 2,
                    (number.height - circle.height) // 2,
                )
                no_number.paste(circle, paste_position, circle)
                no_number.paste(number, (0, 0))
            else:
                no_number = circle

            w, h = number.size
            if not number_hd and circle_hd:
                number = number.resize(
                    (w * 2, h * 2), resample=Image.Resampling.LANCZOS
                )

            x, y = no_number.size
            no_number.paste(number, ((x - w) // 2, (y - h) // 2), number)
            no_number.save(
                os.path.join(
                    self.skin_folder,
                    f"{self.hitcircle_prefix}-{i}{'@2x' if number_hd else ''}.png",
                )
            )
            self.progress_bar.set(0.6 + (i * 0.02))
            self.update()

        default_0, default_0_hd = self.load_skin_element(
            f"{self.hitcircle_prefix}-0", self.backup_dir
        )
        self.progress_bar.set(0.85)
        self.update()

        default_0 = Image.new("RGBA", (no_number.size), (255, 255, 255, 0))
        default_0.save(
            os.path.join(
                self.skin_folder,
                f"{self.hitcircle_prefix}-0{'@2x' if default_0_hd else ''}.png",
            )
        )
        self.progress_bar.set(0.9)
        self.update()

        blank_image = Image.new("RGBA", (1, 1), (255, 255, 255, 0))
        blank_image.save(
            os.path.join(
                self.skin_folder,
                f"hitcircle{'@2x' if hitcircle_hd else ''}.png",
            )
        )
        blank_image.save(
            os.path.join(
                self.skin_folder,
                f"hitcircleoverlay{'@2x' if hitcircleoverlay_hd else ''}.png",
            )
        )
        self.progress_bar.set(0.95)
        self.update()

        try:
            os.remove(os.path.join(self.skin_folder, "circle.png"))
            os.remove(os.path.join(self.skin_folder, "sliderstartcircle.png"))
            os.remove(os.path.join(self.skin_folder, "sliderstartcircle@2x.png"))
            os.remove(os.path.join(self.skin_folder, "sliderstartcircleoverlay.png"))
            os.remove(os.path.join(self.skin_folder, "sliderstartcircleoverlay@2x.png"))
        except FileNotFoundError:
            pass

        self.set_overlap(str(x // 2 if number_hd else x))
        self.set_color(self.selected_color)
        self.add_header()

        self.progress_bar.set(1.0)
        self.update()
        self.after(500, self.progress_bar.grid_remove)

    def get_latest_backup(self) -> str | None:
        """Find the most recent backup folder in the skin directory.

        Returns:
            str | None: Path to most recent backup folder, or None if no backups found
        """
        if not self.skin_folder:
            return None

        backup_folders = [
            d
            for d in os.listdir(self.skin_folder)
            if os.path.isdir(os.path.join(self.skin_folder, d))
            and d.startswith("instafader-backup")
        ]

        if not backup_folders:
            return None

        # Sort by creation time, newest first
        backup_folders.sort(
            key=lambda x: os.path.getctime(os.path.join(self.skin_folder, x)),
            reverse=True,
        )
        return os.path.join(self.skin_folder, backup_folders[0])

    def revert_to_backup(self) -> None:
        """Restore skin files from the most recent backup folder"""
        if not self.skin_folder:
            messagebox.showerror("Error", "No skin folder selected")
            return

        backup_dir = self.get_latest_backup()
        if not backup_dir:
            messagebox.showerror("Error", "No backup found to revert to")
            return

        try:
            self.progress_bar.grid()
            self.progress_bar.set(0)
            self.update()

            backup_files = os.listdir(backup_dir)
            for i, filename in enumerate(backup_files):
                src = os.path.join(backup_dir, filename)
                dst = os.path.join(self.skin_folder, filename)
                shutil.copy2(src, dst)

                progress = (i + 1) / len(backup_files)
                self.progress_bar.set(progress)
                self.update()

            messagebox.showinfo("Success", "Successfully reverted to backup")

            self.load_skin_ini()
            if self.colors:
                self.generate_preview(self.colors[0])

        except Exception as e:
            messagebox.showerror("Error", f"Failed to revert to backup: {e}")
        finally:
            self.progress_bar.grid_remove()

    def add_header(self):
        """Add header to skin.ini file."""
        try:
            skin_ini_path = os.path.join(self.skin_folder, "skin.ini")
            with open(skin_ini_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            header = (
                "// instafade skin generated by https://github.com/SnowzNZ/instafader\n"
            )
            if not any(header.strip() in line for line in lines):
                lines.insert(0, header)  # Add header at the top
                with open(skin_ini_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add header: {e}")


if __name__ == "__main__":
    instafader = Instafader()
    instafader.mainloop()
