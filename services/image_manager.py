import os
import sys
import re
import shutil

class ImageManager:
    def __init__(self):
        """Inicializa o gerenciador fixando o caminho base."""
        self.base_dir = self._calculate_base_path()
        self.img_folder = self.get_image_folder()

    def _calculate_base_path(self):
        """Determina a raiz do projeto de forma absoluta."""
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        
        # Assume que este arquivo está em services/ e sobe um nível
        current_file_path = os.path.abspath(__file__)
        return os.path.dirname(os.path.dirname(current_file_path))

    def get_image_folder(self):
        """Retorna o caminho absoluto da pasta de imagens."""
        folder = os.path.join(self.base_dir, "imagens")
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        return folder

    def clean_filename(self, name):
        """Limpa caracteres inválidos para o Windows."""
        if not name: return ""
        clean = re.sub(r'[\\/*?:"<>|]', "", str(name)).strip()
        return clean

    def find_image_path(self, product_name):
        """Procura a imagem no disco."""
        if not product_name: return None
        safe_name = self.clean_filename(product_name)
        
        for ext in [".jpg", ".png", ".jpeg"]:
            file_path = os.path.join(self.img_folder, f"{safe_name}{ext}")
            if os.path.exists(file_path):
                return file_path
        return None

    def save_image(self, source_path, product_name):
        """Salva a imagem permanentemente no HD."""
        if not source_path or not product_name: return None
        safe_name = self.clean_filename(product_name)
        
        # Remove antigas antes de salvar a nova
        self.delete_image(product_name)

        extension = os.path.splitext(source_path)[1].lower()
        destination = os.path.join(self.img_folder, f"{safe_name}{extension}")
        shutil.copy2(source_path, destination)
        return destination

    def delete_image(self, product_name):
        """Remove fisicamente o arquivo de imagem do disco."""
        safe_name = self.clean_filename(product_name)
        removido = False
        for ext in [".jpg", ".png", ".jpeg"]:
            file_path = os.path.join(self.img_folder, f"{safe_name}{ext}")
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    removido = True
                except Exception as e:
                    print(f"Erro ao deletar arquivo: {e}")
        return removido