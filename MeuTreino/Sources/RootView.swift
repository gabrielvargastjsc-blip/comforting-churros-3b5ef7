import SwiftUI
import SwiftData

// Barra de abas principal. Começa com Treinos e Notas;
// Dieta e Progresso entram na próxima etapa.
struct RootView: View {
    @Environment(\.modelContext) private var context

    var body: some View {
        TabView {
            TreinosView()
                .tabItem { Label("Treinos", systemImage: "dumbbell") }
            NotasView()
                .tabItem { Label("Notas", systemImage: "note.text") }
        }
        .task { SeedData.popularSeVazio(context) }
    }
}
