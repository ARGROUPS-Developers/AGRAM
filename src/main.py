import flet as ft

def main(page: ft.Page):
    page.title = "AGRAM"
    page.bgcolor = "#0D0D0D"
    page.padding = 20
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    page.add(
        ft.Column(
            [
                ft.Text(
                    "AGRAM",
                    size=40,
                    weight=ft.FontWeight.BOLD,
                    color="#00E5FF",
                ),
                ft.Text(
                    "App Successfully Running",
                    size=18,
                    color="#AAAAAA",
                ),
                ft.Container(height=30),
                ft.ElevatedButton(
                    "Test Button",
                    bgcolor="#00E5FF",
                    color="black",
                    on_click=lambda e: page.add(ft.Text("Button Clicked!", color="white")),
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
    )

ft.app(target=main)
