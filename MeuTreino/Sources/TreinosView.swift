import SwiftUI
import SwiftData

// Lista dos seus treinos, mais recentes no topo. Botão + cria um novo.
struct TreinosView: View {
    @Environment(\.modelContext) private var context
    @Query(sort: \Treino.data, order: .reverse) private var treinos: [Treino]

    var body: some View {
        NavigationStack {
            List {
                ForEach(treinos) { treino in
                    NavigationLink(value: treino) {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(treino.nome).font(.headline)
                            Text(treino.data, style: .date)
                                .font(.caption).foregroundStyle(.secondary)
                        }
                    }
                }
                .onDelete(perform: apagar)
            }
            .navigationTitle("Treinos")
            .navigationDestination(for: Treino.self) { treino in
                TreinoDetailView(treino: treino)
            }
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button(action: adicionar) { Image(systemName: "plus") }
                }
            }
            .overlay {
                if treinos.isEmpty {
                    ContentUnavailableView("Sem treinos ainda",
                                           systemImage: "dumbbell",
                                           description: Text("Toque em + para criar o primeiro."))
                }
            }
        }
    }

    private func adicionar() {
        context.insert(Treino(nome: "Novo treino"))
    }

    private func apagar(_ offsets: IndexSet) {
        for i in offsets { context.delete(treinos[i]) }
    }
}
